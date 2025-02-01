from flask import jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
import datetime
import json

# Function to encode a JWT token
def encode_token(user):
    print("encoding token")
    token = create_access_token(
            identity=json.dumps({'user_id': str(user.user_id)}),  # Correctly specifying the identity
            expires_delta=datetime.timedelta(days=2)  # Setting the expiration time
        )    
    return token

# Token-required decorator for securing routes
@jwt_required()
def protected_route():
    current_user = get_jwt_identity()
    print('current_user:', current_user)
    return jsonify(logged_in_as=current_user), 200