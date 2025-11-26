from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from models.user_model import User
import os

#  Local MongoDB
MONGO_URI = "mongodb://localhost:27017"
SESSION_SECRET = "ASHCOSMETICSESSIONSECRETKEY1234567890"
# Initialize FastAPI 
app = FastAPI(title="Ash Cosmetic API", version="2.0")

#  Middleware
#app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET) insted of this we use this->
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",        # REQUIRED for cookies to work
    https_only=False,  
    path="/",    # REQUIRED on localhost
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#  MongoDB Setup 
db = None
users = None

@app.on_event("startup")
async def startup_event():
    global db, users
    print("🔍 Connecting to Local MongoDB...")
    try:
        client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=3000  # 5 sec timeout
        )
        await client.admin.command("ping")
        db = client["ash_legacy"]   # your local DB name
        users = db["users"]
        print("✅ Connected to Local MongoDB!")
    except Exception as e:
        print("❌ MongoDB connection failed:", e)


# Password Hashing 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])  

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)

def require_login(request: Request) -> str:
    """Check if user is logged in"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    return user_id

#ROUTES 
@app.get("/test-db")
async def test_db():
    """Quick MongoDB connection test"""
    try:
        count = await users.count_documents({})
        return {"connected": True, "userCount": count}
    except Exception as e:
        return {"connected": False, "error": str(e)}

#  Registration
@app.post("/submit")
async def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm: str = Form(...)
):
    try:
        if password != confirm:
            return JSONResponse({"success": False, "message": "Passwords do not match"}, status_code=400)

        existing = await users.find_one({"email": email})
        if existing:
            return JSONResponse({"success": False, "message": "Email already registered"}, status_code=400)

        hashed = hash_password(password)
        user = {"name": name, "email": email, "password": hashed, "wishlist": []}
        await users.insert_one(user)
        return JSONResponse({"success": True, "message": "Registration successful!"})
    
    except Exception as e:
        print("❌ Registration error:", e)
        return JSONResponse(
            {"success": False, "message": f"Server error: {str(e)}"},
            status_code=500
        )

#  Login
@app.post("/signin")
async def login_user(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        user = await users.find_one({"email": email})
        if not user:
            return JSONResponse({"success": False, "message": "User not found"}, status_code=400)

        if not verify_password(password, user["password"]):
            return JSONResponse({"success": False, "message": "Invalid password"}, status_code=400)

        request.session["user_id"] = str(user["_id"])
        return JSONResponse({"success": True, "message": "Login successful!"})
    
    except Exception as e:
        print("❌ Login error:", e)
        return JSONResponse(
            {"success": False, "message": f"Server error: {str(e)}"},
            status_code=500
        )

#  Current user
@app.get("/user")
async def get_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return {"loggedIn": False}

    user_doc = await users.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        return {"loggedIn": False}

    user_doc["_id"] = str(user_doc["_id"])  # convert ObjectId
    user_obj = User.model_validate(user_doc)

    return {"loggedIn": True, "user": user_obj}


#  Wishlist - Add
@app.post("/wishlist/add")
async def add_wishlist(
    request: Request,
    productId: str = Form(...),
    name: str = Form(...),
    image: str = Form(...),
    price: float = Form(...)
):
    user_id = require_login(request)
    user = await users.find_one({"_id": ObjectId(user_id)})

    if any(item["productId"] == productId for item in user.get("wishlist", [])):
        return {"success": False, "message": "Already in wishlist"}

    new_item = {"productId": productId, "name": name, "image": image, "price": price}
    user["wishlist"].append(new_item)
    await users.update_one({"_id": ObjectId(user_id)}, {"$set": {"wishlist": user["wishlist"]}})
    return {"success": True, "message": "Added to wishlist"}

#  Wishlist - Remove
@app.post("/wishlist/remove")
async def remove_wishlist(request: Request, productId: str = Form(...)):
    user_id = require_login(request)
    user = await users.find_one({"_id": ObjectId(user_id)})
    updated = [item for item in user.get("wishlist", []) if item["productId"] != productId]
    await users.update_one({"_id": ObjectId(user_id)}, {"$set": {"wishlist": updated}})
    return {"success": True, "message": "Removed from wishlist"}

#  Wishlist - Get All
@app.get("/wishlist")
async def get_wishlist(request: Request):
    user_id = require_login(request)
    user = await users.find_one({"_id": ObjectId(user_id)}, {"wishlist": 1})
    return {"success": True, "wishlist": user.get("wishlist", [])}

#  Logout
@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"success": True, "message": "Logged out"}

#  Serve Frontend
@app.get("/")
async def home():
    return FileResponse("public/index.html")

#  Serve Static Files
app.mount("/public", StaticFiles(directory="public"), name="public")
#   message
print("🚀 Ash Cosmetic API Ready on http://127.0.0.1:8000")
