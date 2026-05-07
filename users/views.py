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
                'message': 'Login Successful'
            })

        # Catch the specific Google Error and print it out
        except ValueError as e:
            print("====== GOOGLE VERIFICATION ERROR ======")
            print(str(e))
            print("=======================================")
            
            # Send the actual error to the frontend red box so we can read it easily
            return Response({'error': f'Invalid Google token: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


class CompleteProfileView(APIView):
    permission_classes = [IsAuthenticated] # User must send their access token to use this

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully!", 
                "is_profile_complete": request.user.profile.is_profile_complete
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)