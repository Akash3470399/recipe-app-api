from django.contrib.auth import get_user_model, authenticate 
from django.utils.translation import gettext as _
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = get_user_model()
        fields = ['email', 'password', 'name']
        extra_kwargs = {
            'password' : {
                'write_only' : True, 'min_length' : 5
            }
        }
        
    def create(self, validated_data):
        
        # we have overrided the create method because
        # by default a serializer will create model instense with provied data and save it
        # but here we don't want password to get save as it is we need to save user with encrypted password
        # so we are using the create user method which create the user with validated data as expected
        print(f"created { validated_data['email']}")
        return get_user_model().objects.create_user(**validated_data)
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        
        if password:
            user.set_password(password)
            user.save()
        return user
        
class AuthTokenSerializer(serializers.Serializer):
    
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        user = authenticate(
            request=self.context.get('request'),
            username = email,
            password = password
        )
        
        if not user:
            msg = _('unable to authenticate wiht provided credentials')
            raise serializers.ValidationError(msg, code='authorization')
        attrs['user'] = user
        return attrs
    
