from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserProfileSerializer

class GoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get('token')
        
        print("====== DEBUGGING TOKEN ======")
        print(f"Token received: {token}")
        
        try:
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                "567107261238-gujakiaj292e4fm7kk5t74k15j1umgno.apps.googleusercontent.com" 
            )

            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            picture = idinfo.get('picture', '')

            if not email:
                return Response({'error': 'Email not provided by Google'}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create the user based on their Google Email
            user, created = User.objects.get_or_create(
                username=email, 
                defaults={'email': email, 'first_name': first_name, 'last_name': last_name}
            )

            # Generate JWT Tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'is_profile_complete': user.profile.is_profile_complete,
                'picture': picture,
                'first_name': user.first_name or first_name,
                'email': user.email or email,
                'phone_number': user.profile.phone_number or '',
                'address': user.profile.address or '',
                'message': 'Login Successful'
            })

        # Catch the specific Google Error and print it out
        except ValueError as e:
            print("====== GOOGLE VERIFICATION ERROR ======")
            print(str(e))
            print("=======================================")
            
            # Send the actual error to the frontend red box so we can read it easily
            return Response({'error': f'Invalid Google token: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework import permissions

class CompleteProfileView(APIView):
    permission_classes = [permissions.AllowAny]

    def put(self, request):
        target_user = request.user if (request.user and request.user.is_authenticated) else None
        
        if not target_user:
            email = request.data.get('email')
            if email:
                target_user = User.objects.filter(email=email).first() or User.objects.filter(username=email).first()
        
        if not target_user:
            return Response({'error': 'Authentication or valid email required.'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = UserProfileSerializer(target_user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully!", 
                "is_profile_complete": target_user.profile.is_profile_complete,
                "first_name": target_user.first_name,
                "email": target_user.email,
                "phone_number": target_user.profile.phone_number,
                "address": target_user.profile.address,
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListUsersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        users = User.objects.all().select_related('profile').order_by('-date_joined')
        data = []
        for u in users:
            profile = getattr(u, 'profile', None)
            data.append({
                'id': u.id,
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'name': f"{u.first_name} {u.last_name}".strip() or u.username,
                'email': u.email or u.username,
                'phone_number': profile.phone_number if profile else '',
                'address': profile.address if profile else '',
                'role': profile.role if profile else 'SEEKER',
                'is_profile_complete': profile.is_profile_complete if profile else False,
                'date_joined': u.date_joined,
            })
        return Response(data, status=status.HTTP_200_OK)