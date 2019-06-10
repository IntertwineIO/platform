# -*- coding: utf-8 -*-
# from flask import Flask, request
# from flask_restful import abort
# from functools import wraps


# def requires_auth(f):
#     @wraps(f)
#     def decorated(*args, **kwargs):
#         auth = request.authorization
#         if not auth:
#             abort(401)
#         user = User.query.filter(User.username == auth.username).first()
#         auth_ok = False
#         if user != None:
#             auth_ok = verify_password(auth.password) == user.password
#         if not auth_ok:
#             return abort(401)
#         return f(*args, **kwargs)
#     return decorated
