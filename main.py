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

from dotenv import load_dotenv
load_dotenv()

#MongoDB Atlas URI 
MONGO_URI = os.getenv("MONGO_URI")
SESSION_SECRET = os.getenv("SESSION_SECRET")

app = FastAPI(title="Ash Cosmetic API", version="2.0")

# Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=False,
    path="/",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mongo Variables
db = None
users = None
products = None   

@app.on_event("startup")
async def startup_event():
    global db, users, products
    print("🔍 Connecting to MongoDB Atlas...")
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client["ash_legacy"]     # database name

        users = db["users"]          
        products = db["products"]     

        print("✅ Connected to MongoDB Atlas!")
    except Exception as e:
        print("❌ MongoDB Atlas connection failed:", e)

# Password Hashing 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])  

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)

def require_login(request: Request) -> str:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    return user_id


# Test DB
@app.get("/test-db")
async def test_db():
    try:
        count = await users.count_documents({})
        return {"connected": True, "userCount": count}
    except Exception as e:
        return {"connected": False, "error": str(e)}

# User registration
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
        return JSONResponse({"success": False, "message": f"Server error: {str(e)}"}, status_code=500)

# login user
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
        return JSONResponse({"success": False, "message": f"Server error: {str(e)}"}, status_code=500)

#product APIs

@app.post("/products/add")
async def add_product(
    productId: str = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    image: str = Form(...)
):
    product = {
        "productId": productId,
        "name": name,
        "description": description,
        "price": price,
        "image": image
    }
    await products.insert_one(product)
    return {"success": True, "message": "Product added!"}

@app.get("/products")
async def get_all_products():
    all_products = []
    async for p in products.find():
        p["_id"] = str(p["_id"])
        all_products.append(p)
    return {"success": True, "products": all_products}

@app.get("/user")
async def get_user(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        return {"loggedIn": False}

    user_doc = await users.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        return {"loggedIn": False}

    user_doc["_id"] = str(user_doc["_id"])
    user_obj = User.model_validate(user_doc)

    return {"loggedIn": True, "user": user_obj}


# Wishlist - Add
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

    # Already exists?
    if any(item["productId"] == productId for item in user.get("wishlist", [])):
        return {"success": False, "message": "Already in wishlist"}

    # New wishlist item
    new_item = {
        "productId": productId,
        "name": name,
        "image": image,
        "price": price
    }

    user["wishlist"].append(new_item)
    await users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"wishlist": user["wishlist"]}}
    )

    return {"success": True, "message": "Added to wishlist"}

# Wishlist - Remove
@app.post("/wishlist/remove")
async def remove_wishlist(request: Request, productId: str = Form(...)):
    user_id = require_login(request)
    user = await users.find_one({"_id": ObjectId(user_id)})

    updated = [item for item in user.get("wishlist", []) if item["productId"] != productId]

    await users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"wishlist": updated}}
    )

    return {"success": True, "message": "Removed from wishlist"}


# Wishlist - Get All
@app.get("/wishlist")
async def get_wishlist(request: Request):
    user_id = require_login(request)
    
    user = await users.find_one(
        {"_id": ObjectId(user_id)},
        {"wishlist": 1}
    )

    return {
        "success": True,
        "wishlist": user.get("wishlist", [])
    }

#  Logout
@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"success": True, "message": "Logged out"}

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def ignore_chrome():
    return {"status": "ok"}

# Serve frontend
@app.get("/")
async def home():
    return FileResponse("public/index.html")

app.mount("/public", StaticFiles(directory="public"), name="public")
