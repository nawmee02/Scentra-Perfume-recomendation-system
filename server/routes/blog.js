import express from 'express';
import { dbAll, dbGet, dbRun } from '../database/init.js';
import { authenticateToken, requireAdmin } from '../middleware/auth.js';

const router = express.Router();

// Get all blog posts
router.get('/', async (req, res) => {
  try {
    const { category, featured, page = 1, limit = 10 } = req.query;

    let query = 'SELECT * FROM blog_posts WHERE published = 1';
    const params = [];

    if (category) {
      query += ' AND category = ?';
      params.push(category);
    }

    if (featured === 'true') {
      query += ' AND featured = 1';
    }

    query += ' ORDER BY created_at DESC';

    // Pagination
    const offset = (parseInt(page) - 1) * parseInt(limit);
    query += ' LIMIT ? OFFSET ?';
    params.push(parseInt(limit), offset);

    const posts = await dbAll(query, params);

    // Get total count
    let countQuery = 'SELECT COUNT(*) as total FROM blog_posts WHERE published = 1';
    const countParams = [];

    if (category) {
      countQuery += ' AND category = ?';
      countParams.push(category);
    }

    if (featured === 'true') {
      countQuery += ' AND featured = 1';
    }

    const { total } = await dbGet(countQuery, countParams);

    res.json({
      posts,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / parseInt(limit))
      }
    });
  } catch (error) {
    console.error('Error fetching blog posts:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get single blog post
router.get('/:id', async (req, res) => {
  try {
    const post = await dbGet('SELECT * FROM blog_posts WHERE id = ? AND published = 1', [req.params.id]);
    
    if (!post) {
      return res.status(404).json({ error: 'Blog post not found' });
    }

    res.json(post);
  } catch (error) {
    console.error('Error fetching blog post:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get blog categories
router.get('/meta/categories', async (req, res) => {
  try {
    const categories = await dbAll(`
      SELECT category, COUNT(*) as count 
      FROM blog_posts 
      WHERE published = 1 
      GROUP BY category 
      ORDER BY category
    `);
    
    res.json(categories);
  } catch (error) {
    console.error('Error fetching blog categories:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create blog post (admin only)
router.post('/', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const { title, excerpt, content, category, image_url, read_time, featured } = req.body;
    const author = req.user.name;

    if (!title || !content || !category) {
      return res.status(400).json({ error: 'Title, content, and category are required' });
    }

    const result = await dbRun(`
      INSERT INTO blog_posts (title, excerpt, content, author, category, image_url, read_time, featured)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `, [title, excerpt, content, author, category, image_url, read_time, featured ? 1 : 0]);

    res.status(201).json({ 
      message: 'Blog post created successfully',
      id: result.id 
    });
  } catch (error) {
    console.error('Error creating blog post:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update blog post (admin only)
router.put('/:id', authenticateToken, requireAdmin, async (req, res) => {
  try {
    const { title, excerpt, content, category, image_url, read_time, featured, published } = req.body;

    await dbRun(`
      UPDATE blog_posts 
      SET title = ?, excerpt = ?, content = ?, category = ?, image_url = ?, 
          read_time = ?, featured = ?, published = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [title, excerpt, content, category, image_url, read_time, featured ? 1 : 0, published ? 1 : 0, req.params.id]);

    res.json({ message: 'Blog post updated successfully' });
  } catch (error) {
    console.error('Error updating blog post:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete blog post (admin only)
router.delete('/:id', authenticateToken, requireAdmin, async (req, res) => {
  try {
    await dbRun('DELETE FROM blog_posts WHERE id = ?', [req.params.id]);
    res.json({ message: 'Blog post deleted successfully' });
  } catch (error) {
    console.error('Error deleting blog post:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;