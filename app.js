// to run use app.js
const express = require('express');
require("dotenv").config();
const mongoose = require('mongoose');
const path = require('path');
const bcrypt = require('bcrypt');
const session = require('express-session');
const User = require('./models/User'); // User model

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Sessions
app.use(
  session({
    secret: process.env.SESSION_SECRET || "defaultsecret",
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      secure: false, //  set true in production with HTTPS
      maxAge: 1000 * 60 * 60, // 1 hour
    },
  })
);
//Don't run without internet connection
// MongoDB Connection
mongoose.connect(process.env.MONGO_URI, {
    // useNewUrlParser: true,
    // useUnifiedTopology: true,
  })
  .then(() => console.log("✅ MongoDB Atlas connected"))
  .catch((err) => console.error("❌ MongoDB Atlas connection error:", err));


// Routes
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/form', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'form.html'));
});

// Registration route
app.post('/submit', async (req, res) => {
  try {
    const { name, email, password, confirm } = req.body;

    if (!name || !email || !password || !confirm) {
      return res.status(400).json({ success: false, message: "All fields required" });
    }

    if (password !== confirm) {
      return res.status(400).json({ success: false, message: "Passwords do not match" });
    }

    const existingUser = await User.findOne({ email });
    if (existingUser) {
      return res.status(400).json({ success: false, message: "Email already registered" });
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const user = new User({ name, email, password: hashedPassword, wishlist: [] });
    await user.save();

    res.json({ success: true, message: "Registration successful!" });
  } catch (err) {
    console.error("Registration error:", err);
    res.status(500).json({ success: false, message: "Error saving user" });
  }
});

// Login route
app.post('/signin', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ success: false, message: "Email & password required" });
    }

    const user = await User.findOne({ email });
    if (!user) {
      return res.status(400).json({ success: false, message: "User not found" });
    }

    const match = await bcrypt.compare(password, user.password);
    if (!match) {
      return res.status(400).json({ success: false, message: "Invalid password" });
    }

    req.session.userId = user._id;
    res.json({ success: true, message: "Login successful!" });
  } catch (err) {
    console.error("Login error:", err);
    res.status(500).json({ success: false, message: "Error logging in" });
  }
});

// Check current user
app.get('/user', async (req, res) => {
  if (!req.session.userId) return res.json({ loggedIn: false });
 try {
    const user = await User.findById(req.session.userId).select("name email wishlist");
    if (!user) return res.json({ loggedIn: false });
    res.json({ loggedIn: true, user });
  } catch (err) {
    console.error("Fetch user error:", err);
    res.json({ loggedIn: false });
  }
});

// Middleware to check login
function requireLogin(req, res, next) {
  if (!req.session.userId) {
    return res.status(401).json({ success: false, message: "Login required" });
  }
  next();
}

// Wishlist routes
app.post('/wishlist/add', requireLogin, async (req, res) => {
  try {
    const { productId, name, image, price } = req.body;
    const user = await User.findById(req.session.userId);

    if (!productId || !name) {
      return res.status(400).json({ success: false, message: "Product data missing" });
    }

    // prevent duplicates
    if (user.wishlist.find(item => item.productId === productId)) {
      return res.json({ success: false, message: "Already in wishlist" });
    }

    user.wishlist.push({ productId, name, image, price });
    await user.save();
    res.json({ success: true, message: "Added to wishlist" });
  } catch (err) {
    console.error("Wishlist add error:", err);
    res.status(500).json({ success: false, message: "Server error" });
  }
});

app.post('/wishlist/remove', requireLogin, async (req, res) => {
  try {
    const { productId } = req.body;
    const user = await User.findById(req.session.userId);

    user.wishlist = user.wishlist.filter(item => item.productId !== productId);
    await user.save();
    res.json({ success: true, message: "Removed from wishlist" });
  } catch (err) {
    console.error("Wishlist remove error:", err);
    res.status(500).json({ success: false, message: "Server error" });
  }
});

app.get('/wishlist', requireLogin, async (req, res) => {
  try {
    const user = await User.findById(req.session.userId);
    res.json({ success: true, wishlist: user.wishlist });
  } catch (err) {
    console.error("Wishlist fetch error:", err);
    res.status(500).json({ success: false, message: "Server error" });
  }
});

// Logout route
app.post('/logout', (req, res) => {
  req.session.destroy(() => {
    res.json({ success: true, message: "Logged out" });
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
});
