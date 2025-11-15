import express from 'express';
import { dbGet } from '../database/init.js';
const router = express.Router();

// Simple in-memory cart for demonstration (replace with DB for production)
let cart = [];

// Add product to cart
router.post('/add', (req, res) => {
  const { perfumeId, quantity } = req.body;
  // Find if product already in cart
  const existing = cart.find(item => item.perfumeId === perfumeId);
  if (existing) {
    existing.quantity += quantity;
  } else {
    cart.push({ perfumeId, quantity });
  }
  res.json({ success: true, cart });
});

// Get cart items
router.get('/', async (req, res) => {
  // Join cart items with perfume details
  const detailedCart = await Promise.all(
    cart.map(async item => {
      const product = await dbGet('SELECT * FROM perfumes WHERE id = ?', [item.perfumeId]);
      return product
        ? { ...product, quantity: item.quantity }
        : null;
    })
  );
  res.json(detailedCart.filter(Boolean));
});

// Remove product from cart
router.post('/remove', (req, res) => {
  const { perfumeId } = req.body;
  cart = cart.filter(item => item.perfumeId !== perfumeId);
  res.json({ success: true, cart });
});

// Update quantity
router.post('/update', (req, res) => {
  const { perfumeId, quantity } = req.body;
  const item = cart.find(item => item.perfumeId === perfumeId);
  if (item) item.quantity = quantity;
  res.json({ success: true, cart });
});

export default router;