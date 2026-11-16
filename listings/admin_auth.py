"""
Admin sign-in with 2-step verification by email code.

Step 1  POST /api/auth/admin/login/       {username, password, device_token?}
        - wrong password            -> 401
        - not the main admin         -> 403
        - trusted device (remembered) -> tokens straight away
        - otherwise                  -> an email with a 6-digit code, returns {otp_required, challenge_id}
Step 2  POST /api/auth/admin/verify-otp/  {challenge_id, code, remember_device}
        - correct code -> tokens (+ device_token for 30 days when remember_device is true)

Normal /api/auth/login/ refuses superusers, so the admin can't skip the code.
"""
import hashlib
import os
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .emailer import EmailNotConfigured, EmailSendFailed, send_email
from .models import AdminLoginOTP, TrustedAdminDevice

OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_SECONDS = 45
OTP_MAX_PER_HOUR = 8
TRUSTED_DEVICE_DAYS = int(os.environ.get('ADMIN_TRUSTED_DEVICE_DAYS', '30'))


def _hash(value):
    key = os.environ.get('JWT_SIGNING_KEY') or settings.SECRET_KEY
    return hashlib.sha256(f"{key}:{value}".encode()).hexdigest()


def _tokens(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


def _mask_email(email):
    name, _, domain = (email or '').partition('@')
    if not domain:
        return ''
    shown = name[:2] if len(name) > 2 else name[:1]
    return f"{shown}{'*' * max(3, len(name) - len(shown))}@{domain}"


def _otp_email_for(user):
    # Optional override so the code can go to a different inbox than the account email
    return os.environ.get('ADMIN_OTP_EMAIL') or user.email


class AdminTokenObtainSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.is_superuser:
            raise AuthenticationFailed('Admin accounts must sign in from the admin page with the email code.')
        return data


class NoAdminTokenObtainPairView(TokenObtainPairView):
    """Used for /api/auth/login/ (staff and normal accounts). Blocks the admin from skipping 2-step."""
    serializer_class = AdminTokenObtainSerializer


class AdminLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_login'

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        device_token = (request.data.get('device_token') or '').strip()

        user = authenticate(request, username=username, password=password)
        if not user or not user.is_active:
            return Response({'error': 'Wrong username or password.'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_superuser:
            return Response({'error': 'This account is not an admin account.'}, status=status.HTTP_403_FORBIDDEN)

        # Remembered device: skip the email code
        if device_token:
            device = TrustedAdminDevice.objects.filter(
                user=user, token_hash=_hash(device_token), expires_at__gt=timezone.now()
            ).first()
            if device:
                device.last_used_at = timezone.now()
                device.save(update_fields=['last_used_at'])
                return Response({'otp_required': False, **_tokens(user)}, status=status.HTTP_200_OK)

        to_email = _otp_email_for(user)
        if not to_email:
            return Response({'error': 'The admin account has no email address for the sign-in code.'},
                            status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        recent = AdminLoginOTP.objects.filter(user=user, created_at__gt=now - timedelta(hours=1))
        if recent.count() >= OTP_MAX_PER_HOUR:
            return Response({'error': 'Too many codes requested. Please wait an hour and try again.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        last = recent.order_by('-created_at').first()
        if last and (now - last.created_at).total_seconds() < OTP_RESEND_SECONDS:
            wait = int(OTP_RESEND_SECONDS - (now - last.created_at).total_seconds()) + 1
            return Response({'error': f'Please wait {wait} seconds before asking for a new code.', 'retry_after': wait},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge_id = secrets.token_urlsafe(24)
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:420px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px">
          <h2 style="margin:0 0 8px;color:#0f2c59">SetMyStay admin sign-in</h2>
          <p style="color:#374151">Your sign-in code is:</p>
          <p style="font-size:32px;letter-spacing:8px;font-weight:bold;color:#1d4ed8;margin:12px 0">{code}</p>
          <p style="color:#6b7280;font-size:13px">It expires in {OTP_TTL_MINUTES} minutes. If you did not try to sign in,
          someone knows your admin password: change it right away.</p>
        </div>"""
        try:
            send_email(to_email, f'{code} is your SetMyStay admin code', html,
                       text=f'Your SetMyStay admin sign-in code is {code}. It expires in {OTP_TTL_MINUTES} minutes.')
        except EmailNotConfigured:
            return Response({'error': 'Email sending is not set up on the server yet (BREVO_API_KEY / BREVO_SENDER_EMAIL).'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except EmailSendFailed as e:
            print('Admin OTP email failed:', e)
            return Response({'error': 'Could not send the email code. Please try again in a minute.'},
                            status=status.HTTP_502_BAD_GATEWAY)

        AdminLoginOTP.objects.create(
            user=user,
            purpose='login',
            challenge_id=challenge_id,
            code_hash=_hash(f"{challenge_id}:{code}"),
            expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
        )
        return Response({
            'otp_required': True,
            'challenge_id': challenge_id,
            'email_hint': _mask_email(to_email),
            'expires_in_minutes': OTP_TTL_MINUTES,
            'resend_after_seconds': OTP_RESEND_SECONDS,
        }, status=status.HTTP_200_OK)


class AdminVerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_otp'

    def post(self, request):
        challenge_id = (request.data.get('challenge_id') or '').strip()
        code = ''.join(ch for ch in str(request.data.get('code') or '') if ch.isdigit())
        remember = str(request.data.get('remember_device')).lower() in ('true', '1', 'yes')

        with transaction.atomic():
            otp = AdminLoginOTP.objects.select_for_update().filter(challenge_id=challenge_id, purpose='login').first()
            if not otp or otp.used:
                return Response({'error': 'This code is no longer valid. Please sign in again.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if otp.expires_at <= timezone.now():
                return Response({'error': 'The code has expired. Please sign in again.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if otp.attempts >= OTP_MAX_ATTEMPTS:
                return Response({'error': 'Too many wrong codes. Please sign in again.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if not secrets.compare_digest(otp.code_hash, _hash(f"{challenge_id}:{code}")):
                otp.attempts += 1
                otp.save(update_fields=['attempts'])
                left = OTP_MAX_ATTEMPTS - otp.attempts
                return Response({'error': f'Wrong code. {left} tries left.' if left > 0 else 'Too many wrong codes. Please sign in again.'},
                                status=status.HTTP_400_BAD_REQUEST)
            otp.used = True
            otp.save(update_fields=['used'])

        user = otp.user
        if not (user.is_active and user.is_superuser):
            return Response({'error': 'This account is not an admin account.'}, status=status.HTTP_403_FORBIDDEN)

        payload = {'otp_required': False, **_tokens(user)}
        if remember:
            raw = secrets.token_urlsafe(32)
            TrustedAdminDevice.objects.create(
                user=user,
                token_hash=_hash(raw),
                label=(request.META.get('HTTP_USER_AGENT') or '')[:200],
                expires_at=timezone.now() + timedelta(days=TRUSTED_DEVICE_DAYS),
            )
            payload['device_token'] = raw
            payload['device_days'] = TRUSTED_DEVICE_DAYS
        # Old codes are no longer needed
        AdminLoginOTP.objects.filter(user=user, created_at__lt=timezone.now() - timedelta(days=1)).delete()
        return Response(payload, status=status.HTTP_200_OK)


class AdminForgetDevicesView(APIView):
    """Admin > Security: sign out of all remembered devices (they will need the email code again)."""

    def get_permissions(self):
        from .permissions import IsSuperAdmin
        return [IsSuperAdmin()]

    def post(self, request):
        n, _ = TrustedAdminDevice.objects.filter(user=request.user).delete()
        return Response({'status': 'success', 'removed': n}, status=status.HTTP_200_OK)


class AdminForgetThisDeviceView(APIView):
    """Admin > 'Require code on this device': this browser stops skipping the email code.
    Body: {"device_token": "<this browser's remembered-device token>"}"""

    def get_permissions(self):
        from .permissions import IsSuperAdmin
        return [IsSuperAdmin()]

    def post(self, request):
        token = str(request.data.get('device_token') or '').strip()
        removed = 0
        if token:
            removed, _ = TrustedAdminDevice.objects.filter(user=request.user, token_hash=_hash(token)).delete()
        return Response({'status': 'success', 'removed': removed}, status=status.HTTP_200_OK)


def _code_email_html(title, intro, code, footer):
    return f"""
        <div style="font-family:Arial,sans-serif;max-width:420px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px">
          <h2 style="margin:0 0 8px;color:#0f2c59">{title}</h2>
          <p style="color:#374151">{intro}</p>
          <p style="font-size:32px;letter-spacing:8px;font-weight:bold;color:#1d4ed8;margin:12px 0">{code}</p>
          <p style="color:#6b7280;font-size:13px">{footer}</p>
        </div>"""


class AdminForgotPasswordView(APIView):
    """
    Step 1 of 'Forgot password': emails a 6-digit reset code to the admin email.
    Always answers the same way, so nobody can use it to find out which usernames exist.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_login'

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        challenge_id = secrets.token_urlsafe(24)
        generic = {
            'challenge_id': challenge_id,
            'message': 'If this is an admin account, a reset code has been sent to its email.',
            'expires_in_minutes': OTP_TTL_MINUTES,
            'resend_after_seconds': OTP_RESEND_SECONDS,
        }
        user = get_user_model().objects.filter(username=username, is_active=True, is_superuser=True).first()
        to_email = _otp_email_for(user) if user else ''
        if not user or not to_email:
            return Response(generic, status=status.HTTP_200_OK)

        now = timezone.now()
        recent = AdminLoginOTP.objects.filter(user=user, created_at__gt=now - timedelta(hours=1))
        if recent.count() >= OTP_MAX_PER_HOUR:
            return Response({'error': 'Too many codes requested. Please wait an hour and try again.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        last = recent.order_by('-created_at').first()
        if last and (now - last.created_at).total_seconds() < OTP_RESEND_SECONDS:
            wait = int(OTP_RESEND_SECONDS - (now - last.created_at).total_seconds()) + 1
            return Response({'error': f'Please wait {wait} seconds before asking for a new code.', 'retry_after': wait},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        code = f"{secrets.randbelow(1_000_000):06d}"
        html = _code_email_html(
            'SetMyStay admin password reset',
            'Use this code to set a new admin password:',
            code,
            f'It expires in {OTP_TTL_MINUTES} minutes. If you did not ask to reset the password, ignore this email; '
            'your password stays the same.',
        )
        try:
            send_email(to_email, f'{code} is your SetMyStay password reset code', html,
                       text=f'Your SetMyStay admin password reset code is {code}. It expires in {OTP_TTL_MINUTES} minutes.')
        except EmailNotConfigured:
            return Response({'error': 'Email sending is not set up on the server yet.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except EmailSendFailed as e:
            print('Admin reset email failed:', e)
            return Response({'error': 'Could not send the email code. Please try again in a minute.'},
                            status=status.HTTP_502_BAD_GATEWAY)

        AdminLoginOTP.objects.create(
            user=user, challenge_id=challenge_id, purpose='reset',
            code_hash=_hash(f"{challenge_id}:{code}"),
            expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
        )
        return Response({**generic, 'email_hint': _mask_email(to_email)}, status=status.HTTP_200_OK)


class AdminResetPasswordView(APIView):
    """Step 2 of 'Forgot password': checks the emailed code and sets the new password."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_otp'

    def post(self, request):
        challenge_id = (request.data.get('challenge_id') or '').strip()
        code = ''.join(ch for ch in str(request.data.get('code') or '') if ch.isdigit())
        new_password = request.data.get('new_password') or ''

        with transaction.atomic():
            otp = AdminLoginOTP.objects.select_for_update().filter(challenge_id=challenge_id, purpose='reset').first()
            if not otp or otp.used:
                return Response({'error': 'Wrong code. Please check the email or ask for a new code.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if otp.expires_at <= timezone.now():
                return Response({'error': 'The code has expired. Please ask for a new code.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if otp.attempts >= OTP_MAX_ATTEMPTS:
                return Response({'error': 'Too many wrong codes. Please ask for a new code.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if not secrets.compare_digest(otp.code_hash, _hash(f"{challenge_id}:{code}")):
                otp.attempts += 1
                otp.save(update_fields=['attempts'])
                left = OTP_MAX_ATTEMPTS - otp.attempts
                return Response({'error': f'Wrong code. {left} tries left.' if left > 0 else 'Too many wrong codes. Please ask for a new code.'},
                                status=status.HTTP_400_BAD_REQUEST)

            user = otp.user
            try:
                validate_password(new_password, user=user)
            except ValidationError as e:
                # Code was right; let them try another password with the same code
                return Response({'error': ' '.join(e.messages), 'password_error': True},
                                status=status.HTTP_400_BAD_REQUEST)

            otp.used = True
            otp.save(update_fields=['used'])
            user.set_password(new_password)
            user.save(update_fields=['password'])
            # Sign out every remembered device; the admin signs in again with the new password
            TrustedAdminDevice.objects.filter(user=user).delete()

        return Response({'status': 'success', 'message': 'Password changed. Please sign in with your new password.'},
                        status=status.HTTP_200_OK)
