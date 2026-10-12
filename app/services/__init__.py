"""Business logic layer.

Services hold the rules of the CRM (permissions, validation, side effects such as
logging an activity when a deal changes stage). They take a DB session and plain
arguments, know nothing about HTTP, and are called by the routers.
"""
