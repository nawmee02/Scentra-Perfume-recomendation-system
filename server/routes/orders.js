import express from 'express';
import { dbRun, dbGet, dbAll } from '../database/init.js';
import { authenticateToken, requireAdmin } from '../middleware/auth.js';

const router = express.Router();

// Create order
router.post('/', authenticateToken, async (req, res) => {
  try {
    const { items, shippingAddress, paymentMethod } = req.body;
    const userId = req.user.id;

    if (!items || !Array.isArray(items) || items.length === 0) {
      return res.status(400).json({ error: 'Order items are required' });
    }

    // Calculate total amount
    let totalAmount = 0;
    const orderItems = [];

    for (const item of items) {
      const perfume = await dbGet('SELECT * FROM perfumes WHERE id = ?', [item.perfumeId]);
      
      if (!perfume) {
        return res.status(400).json({ error: `Perfume with ID ${item.perfumeId} not found` });
      }

      if (!perfume.in_stock) {
        return res.status(400).json({ error: `${perfume.name} is out of stock` });
      }

      const itemTotal = perfume.price * item.quantity;
      totalAmount += itemTotal;

      orderItems.push({
        perfume_id: item.perfumeId,
        quantity: item.quantity,
        price: perfume.price,
        size: item.size || null
      });
    }

    // Create order
    const orderResult = await dbRun(`
      INSERT INTO orders (user_id, total_amount, shipping_address, payment_method)
      VALUES (?, ?, ?, ?)
    `, [userId, totalAmount, JSON.stringify(shippingAddress), paymentMethod]);

    const orderId = orderResult.id;

    // Add order items
    for (const item of orderItems) {
      await dbRun(`
        INSERT INTO order_items (order_id, perfume_id, quantity, price, size)
        VALUES (?, ?, ?, ?, ?)
      `, [orderId, item.perfume_id, item.quantity, item.price, item.size]);
    }

    res.status(201).json({
      message: 'Order created successfully',
      orderId,
      totalAmount
    });
  } catch (error) {
    console.error('Error creating order:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get order by ID
router.get('/:id', authenticateToken, async (req, res) => {
  try {
    const orderId = req.params.id;
    const userId = req.user.id;

    // Get order (ensure user owns the order or is admin)
    let orderQuery = 'SELECT * FROM orders WHERE id = ?';
    let orderParams = [orderId];

    if (req.user.role !== 'admin') {
      orderQuery += ' AND user_id = ?';
      orderParams.push(userId);
    }

    const order = await dbGet(orderQuery, orderParams);

    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    // Get order items
    const items = await dbAll(`
      SELECT oi.*, p.name, p.brand, p.image_url
      FROM order_items oi
      JOIN perfumes p ON oi.perfume_id = p.id
      WHERE oi.order_id = ?
    `, [orderId]);

    // Parse shipping address
    if (order.shipping_address) {
      order.shipping_address = JSON.parse(order.shipping_address);
    }

    res.json({
      ...order,
      items
    });
  } catch (error) {
    console.error('Error fetching order:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update order status (admin only)
router.put('/:id/status', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const { status, paymentStatus } = req.body;
    const orderId = req.params.id;

    const validStatuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled'];
    const validPaymentStatuses = ['pending', 'paid', 'failed', 'refunded'];

    if (status && !validStatuses.includes(status)) {
      return res.status(400).json({ error: 'Invalid order status' });
    }

    if (paymentStatus && !validPaymentStatuses.includes(paymentStatus)) {
      return res.status(400).json({ error: 'Invalid payment status' });
    }

    await dbRun(`
      UPDATE orders 
      SET status = COALESCE(?, status), 
          payment_status = COALESCE(?, payment_status),
          updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [status, paymentStatus, orderId]);

    res.json({ message: 'Order status updated successfully' });
  } catch (error) {
    console.error('Error updating order status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get all orders (admin only)
router.get('/', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const { status, page = 1, limit = 20 } = req.query;

    let query = `
      SELECT o.*, u.name as user_name, u.email as user_email
      FROM orders o
      JOIN users u ON o.user_id = u.id
      WHERE 1=1
    `;
    const params = [];

    if (status) {
      query += ' AND o.status = ?';
      params.push(status);
    }

    query += ' ORDER BY o.created_at DESC';

    // Pagination
    const offset = (parseInt(page) - 1) * parseInt(limit);
    query += ' LIMIT ? OFFSET ?';
    params.push(parseInt(limit), offset);

    const orders = await dbAll(query, params);

    // Get total count
    let countQuery = 'SELECT COUNT(*) as total FROM orders WHERE 1=1';
    const countParams = [];

    if (status) {
      countQuery += ' AND status = ?';
      countParams.push(status);
    }

    const { total } = await dbGet(countQuery, countParams);

    res.json({
      orders,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / parseInt(limit))
      }
    });
  } catch (error) {
    console.error('Error fetching orders:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;