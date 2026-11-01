import express from 'express';
import { dbGet, dbAll, dbRun } from '../database/init.js';
import { optionalAuth } from '../middleware/auth.js';

const router = express.Router();
router.use(optionalAuth);

function getCartCondition(req) {
  if (req.user && req.user.id) {
    return { sql: 'user_id = ?', params: [req.user.id] };
  }
  const sessionId = req.headers['x-session-id'] || 'guest';
  return { sql: 'session_id = ?', params: [sessionId] };
}

// Get cart items with full perfume details
router.get('/', async (req, res) => {
  try {
    const { sql, params } = getCartCondition(req);
    const rows = await dbAll(`
      SELECT c.id as cart_id, c.quantity, c.perfume_id,
             p.name, p.brand, p.price, p.original_price, p.image_url,
             p.category, p.notes, p.sizes, p.in_stock, p.discount
      FROM cart c
      JOIN perfumes p ON c.perfume_id = p.id
      WHERE c.${sql}
      ORDER BY c.created_at DESC
    `, params);

    const detailedCart = rows.map(item => ({
      id: item.perfume_id,
      cartId: item.cart_id,
      name: item.name,
      brand: item.brand,
      price: item.price,
      original_price: item.original_price,
      image_url: item.image_url,
      category: item.category,
      notes: JSON.parse(item.notes || '[]'),
      sizes: JSON.parse(item.sizes || '[]'),
      inStock: Boolean(item.in_stock),
      discount: item.discount,
      quantity: item.quantity,
    }));

    res.json(detailedCart);
  } catch (err) {
    console.error('Error fetching cart:', err);
    res.status(500).json({ error: 'Failed to fetch cart' });
  }
});

// Add product to cart
router.post('/add', async (req, res) => {
  try {
    const { perfumeId, quantity = 1 } = req.body;
    if (!perfumeId) {
      return res.status(400).json({ error: 'perfumeId is required' });
    }

    const perfume = await dbGet('SELECT id, in_stock FROM perfumes WHERE id = ?', [perfumeId]);
    if (!perfume) {
      return res.status(404).json({ error: 'Perfume not found' });
    }

    const { sql, params } = getCartCondition(req);
    const existing = await dbGet(`SELECT id, quantity FROM cart WHERE perfume_id = ? AND ${sql}`, [perfumeId, ...params]);

    if (existing) {
      await dbRun(
        'UPDATE cart SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        [parseInt(quantity) || 1, existing.id]
      );
    } else {
      const userId = req.user ? req.user.id : null;
      const sessionId = req.user ? null : (req.headers['x-session-id'] || 'guest');
      await dbRun(
        'INSERT INTO cart (user_id, session_id, perfume_id, quantity) VALUES (?, ?, ?, ?)',
        [userId, sessionId, perfumeId, parseInt(quantity) || 1]
      );
    }

    res.json({ success: true, message: 'Item added to cart' });
  } catch (err) {
    console.error('Error adding to cart:', err);
    res.status(500).json({ error: 'Failed to add item to cart' });
  }
});

// Update item quantity
router.post('/update', async (req, res) => {
  try {
    const { perfumeId, quantity } = req.body;
    if (!perfumeId) {
      return res.status(400).json({ error: 'perfumeId is required' });
    }

    const { sql, params } = getCartCondition(req);
    const qty = parseInt(quantity);

    if (qty <= 0) {
      await dbRun(`DELETE FROM cart WHERE perfume_id = ? AND ${sql}`, [perfumeId, ...params]);
    } else {
      await dbRun(
        `UPDATE cart SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE perfume_id = ? AND ${sql}`,
        [qty, perfumeId, ...params]
      );
    }

    res.json({ success: true, message: 'Cart updated' });
  } catch (err) {
    console.error('Error updating cart:', err);
    res.status(500).json({ error: 'Failed to update cart' });
  }
});

// Remove product from cart
router.post('/remove', async (req, res) => {
  try {
    const { perfumeId } = req.body;
    if (!perfumeId) {
      return res.status(400).json({ error: 'perfumeId is required' });
    }

    const { sql, params } = getCartCondition(req);
    await dbRun(`DELETE FROM cart WHERE perfume_id = ? AND ${sql}`, [perfumeId, ...params]);

    res.json({ success: true, message: 'Item removed from cart' });
  } catch (err) {
    console.error('Error removing from cart:', err);
    res.status(500).json({ error: 'Failed to remove item from cart' });
  }
});

// Clear cart
router.post('/clear', async (req, res) => {
  try {
    const { sql, params } = getCartCondition(req);
    await dbRun(`DELETE FROM cart WHERE ${sql}`, params);
    res.json({ success: true, message: 'Cart cleared' });
  } catch (err) {
    console.error('Error clearing cart:', err);
    res.status(500).json({ error: 'Failed to clear cart' });
  }
});

export default router;
