def getPassword() -> str:

    return "secret_password"  


def login(password: str) -> bool:
    if password == getPassword():
        return True
    else:
        return False


tools_schemas = [
    {
        "type": "function",
        "name": "login",
        "description": "Checks if a given password matches the secret password.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
            "password": {
                "type": "string",
                "description": "The password to validate."
            }
            },
            "required": [
            "password"
            ],
            "additionalProperties": False
        }
    }, 
    {
        "type": "function",
        "name": "getPassword",
        "description": "Return a secret password string",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    }

]

## Export funtions for testing
__all__ = ["getPassword", "login", "tools_schemas"]
