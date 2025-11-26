// product.js

// Product data
const products = {
  prod1: { name: "Clothes", price: "₹999", description: "Trendy and comfortable clothes for all seasons. High-quality fabric with premium stitching.", image: "images/box1_image.jpg" },
  prod2: { name: "Health Care", price: "₹999", description: "Top-quality healthcare products to keep you and your family safe and healthy.", image: "images/box2_image.jpg" },
  prod3: { name: "Furniture", price: "₹999", description: "Elegant and modern furniture that fits every home and style.", image: "images/box3_image.jpg" },
  prod4: { name: "Electronics", price: "₹999", description: "Latest gadgets and electronics with unbeatable deals and warranties.", image: "images/box4_image.jpg" },
  prod5: { name: "Beauty Picks", price: "₹999", description: "Exclusive beauty and skincare products to enhance your natural glow.", image: "images/box5_image.jpg" },
  prod6: { name: "Pet Care", price: "₹999", description: "Care and grooming essentials for your furry friends.", image: "images/box6_image.jpg" },
  prod7: { name: "New Arrivals Toys", price: "₹999", description: "Fun and safe toys that spark imagination and joy.", image: "images/box7_image.jpg" },
  prod8: { name: "Fashion Trends", price: "₹999", description: "Stay ahead in style with the latest fashion collections.", image: "images/box8_image.jpg" },
  prod9: { name: "Jewelry Trends", price: "₹999", description: "Shine bright with our elegant and timeless jewelry collection.", image: "images/box9_image.jpg" }
};

// Read product ID 
const params = new URLSearchParams(window.location.search);
const productId = params.get("id");

// Elements
const img = document.getElementById("product-image");
const nameEl = document.getElementById("product-name");
const priceEl = document.getElementById("product-price");
const descEl = document.getElementById("product-description");
const wishlistBtn = document.getElementById("addToWishlist");
const buyBtn = document.getElementById("buyNow");

// Load product data
if (productId && products[productId]) {
  const p = products[productId];
  img.src = p.image;
  nameEl.textContent = p.name;
  priceEl.textContent = p.price;
  descEl.textContent = p.description;

  // Very important: add dataset.id to this button
  wishlistBtn.dataset.id = productId;

} else {
  document.body.innerHTML = "<h2 style='text-align:center;color:red;'>Product Not Found</h2>";
}

// Add to Wishlist
wishlistBtn.addEventListener("click", async () => {

  const id = wishlistBtn.dataset.id;   //product id from button
  const p = products[id];

  if (!p) {
    alert("Product not found!");
    return;
  }

  const formData = new FormData();
  formData.append("productId", id);   //(use id here to avoid duplicates in wishlist)
  formData.append("name", p.name);
  formData.append("image", p.image);

  const numericPrice = p.price.replace("₹", "").replace(/,/g, "");
  formData.append("price", parseFloat(numericPrice));

  const res = await fetch("/wishlist/add", {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  const result = await res.json();
  alert(result.success ? `✅ ${p.name} added to wishlist!` : result.message);
});

// Buy Now
buyBtn.addEventListener("click", async (e) => {
  e.preventDefault();
  try {
    const res = await fetch("/user", { credentials: "include" });
    const data = await res.json();

    if (data.loggedIn) {
      window.location.href = `payment.html?id=${productId}`;
    } else {
      alert("⚠️ Please log in to continue with your order.");
      window.location.href = "form.html";
    }
  } catch (err) {
    alert("❌ Network error.");
  }
});

// Wishlist navigation
document.getElementById("wishlistNav").addEventListener("click", () => {
  window.location.href = "wishlist.html";
});

// User login status
async function checkUser() {
  try {
    const res = await fetch("/user", { credentials: "include" });
    const data = await res.json();
    const customerBtn = document.getElementById("customer");

    if (data.loggedIn) {
      customerBtn.innerHTML = `Hello, ${data.user.name}<br><b>Sign Out</b>`;
      customerBtn.onclick = async () => {
        await fetch("/logout", { method: "POST", credentials: "include" });
        window.location.reload();
      };
    } else {
      customerBtn.innerHTML = `Sign In<br><b>Accounts & Lists</b>`;
      customerBtn.onclick = () => {
        window.location.href = "form.html";
      };
    }
  } catch (err) {
    console.error("User check failed:", err);
  }
}

checkUser();
