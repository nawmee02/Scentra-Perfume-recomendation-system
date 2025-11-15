import express from 'express';
import bcrypt from 'bcryptjs';
import { dbGet, dbRun, dbAll } from '../database/init.js';
import { authenticateToken } from '../middleware/auth.js';

const router = express.Router();

// Get user profile
router.get('/profile', authenticateToken, async (req, res) => {
  try {
    const user = await dbGet(
      'SELECT id, name, email, role, avatar, preferences, created_at FROM users WHERE id = ?',
      [req.user.id]
    );

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Parse preferences if they exist
    if (user.preferences) {
      user.preferences = JSON.parse(user.preferences);
    }

    res.json(user);
  } catch (error) {
    console.error('Error fetching user profile:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update user profile
router.put('/profile', authenticateToken, async (req, res) => {
  try {
    const { name, email, preferences } = req.body;
    const userId = req.user.id;

    // Check if email is already taken by another user
    if (email) {
      const existingUser = await dbGet(
        'SELECT id FROM users WHERE email = ? AND id != ?',
        [email, userId]
      );

      if (existingUser) {
        return res.status(400).json({ error: 'Email already taken' });
      }
    }

    // Update user
    await dbRun(`
      UPDATE users 
      SET name = COALESCE(?, name), 
          email = COALESCE(?, email), 
          preferences = COALESCE(?, preferences),
          updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [name, email, preferences ? JSON.stringify(preferences) : null, userId]);

    res.json({ message: 'Profile updated successfully' });
  } catch (error) {
    console.error('Error updating profile:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Change password
router.put('/password', authenticateToken, async (req, res) => {
  try {
    const { currentPassword, newPassword } = req.body;
    const userId = req.user.id;

    if (!currentPassword || !newPassword) {
      return res.status(400).json({ error: 'Current and new passwords are required' });
    }

    if (newPassword.length < 6) {
      return res.status(400).json({ error: 'New password must be at least 6 characters' });
    }

    // Get current password hash
    const user = await dbGet('SELECT password FROM users WHERE id = ?', [userId]);
    
    // Verify current password
    const isValidPassword = await bcrypt.compare(currentPassword, user.password);
    if (!isValidPassword) {
      return res.status(400).json({ error: 'Current password is incorrect' });
    }

    // Hash new password
    const hashedNewPassword = await bcrypt.hash(newPassword, 10);

    // Update password
    await dbRun(
      'UPDATE users SET password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
      [hashedNewPassword, userId]
    );

    res.json({ message: 'Password updated successfully' });
  } catch (error) {
    console.error('Error updating password:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get user wishlist
router.get('/wishlist', authenticateToken, async (req, res) => {
  try {
    const wishlist = await dbAll(`
      SELECT p.*, w.created_at as added_at
      FROM wishlist w
      JOIN perfumes p ON w.perfume_id = p.id
      WHERE w.user_id = ?
      ORDER BY w.created_at DESC
    `, [req.user.id]);

    // Format perfumes
    const formattedWishlist = wishlist.map(item => ({
      ...item,
      notes: JSON.parse(item.notes || '[]'),
      sizes: JSON.parse(item.sizes || '[]'),
      inStock: Boolean(item.in_stock)
    }));

    res.json(formattedWishlist);
  } catch (error) {
    console.error('Error fetching wishlist:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Add to wishlist
router.post('/wishlist/:perfumeId', authenticateToken, async (req, res) => {
  try {
    const { perfumeId } = req.params;
    const userId = req.user.id;

    // Check if perfume exists
    const perfume = await dbGet('SELECT id FROM perfumes WHERE id = ?', [perfumeId]);
    if (!perfume) {
      return res.status(404).json({ error: 'Perfume not found' });
    }

    // Check if already in wishlist
    const existing = await dbGet(
      'SELECT id FROM wishlist WHERE user_id = ? AND perfume_id = ?',
      [userId, perfumeId]
    );

    if (existing) {
      return res.status(400).json({ error: 'Perfume already in wishlist' });
    }

    // Add to wishlist
    await dbRun(
      'INSERT INTO wishlist (user_id, perfume_id) VALUES (?, ?)',
      [userId, perfumeId]
    );

    res.status(201).json({ message: 'Added to wishlist successfully' });
  } catch (error) {
    console.error('Error adding to wishlist:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Remove from wishlist
router.delete('/wishlist/:perfumeId', authenticateToken, async (req, res) => {
  try {
    const { perfumeId } = req.params;
    const userId = req.user.id;

    await dbRun(
      'DELETE FROM wishlist WHERE user_id = ? AND perfume_id = ?',
      [userId, perfumeId]
    );

    res.json({ message: 'Removed from wishlist successfully' });
  } catch (error) {
    console.error('Error removing from wishlist:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get user orders
router.get('/orders', authenticateToken, async (req, res) => {
  try {
    const orders = await dbAll(`
      SELECT o.*, 
             json_group_array(
               json_object(
                 'perfume_id', oi.perfume_id,
                 'perfume_name', p.name,
                 'brand', p.brand,
                 'quantity', oi.quantity,
                 'price', oi.price,
                 'size', oi.size,
                 'image_url', p.image_url
               )
             ) as items
      FROM orders o
      LEFT JOIN order_items oi ON o.id = oi.order_id
      LEFT JOIN perfumes p ON oi.perfume_id = p.id
      WHERE o.user_id = ?
      GROUP BY o.id
      ORDER BY o.created_at DESC
    `, [req.user.id]);

    const formattedOrders = orders.map(order => ({
      ...order,
      items: order.items ? JSON.parse(order.items) : []
    }));

    res.json(formattedOrders);
  } catch (error) {
    console.error('Error fetching user orders:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;