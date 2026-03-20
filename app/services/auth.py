from app.models.user import User, UserRole

class AuthService:
    @staticmethod
    async def authenticate_user(email: str, password: str):
        user = await User.find_one(User.email == email)
        if not user: return None
        if user.password != password: return None
        return user

    @staticmethod
    async def create_user(email: str, password: str, role: UserRole, name: str) -> User:
        existing_user = await User.find_one(User.email == email)
        if existing_user:
            return None

        new_user = User(
            email=email,
            password=password,
            role=role,
            name=name
        )
        await new_user.insert()
        return new_user