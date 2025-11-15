import express from 'express';
import { dbAll, dbGet, dbRun } from '../database/init.js';
import { authenticateToken, requireAdmin } from '../middleware/auth.js';

const router = express.Router();

// Get all perfumes with filtering and search
router.get('/', async (req, res) => {
  try {
    const { 
      search, 
      category, 
      brand, 
      minPrice, 
      maxPrice, 
      notes, 
      sortBy = 'featured',
      page = 1,
      limit = 12 
    } = req.query;

    let query = 'SELECT * FROM perfumes WHERE 1=1';
    const params = [];

    // Search filter
    if (search) {
      query += ' AND (name LIKE ? OR brand LIKE ? OR description LIKE ?)';
      const searchTerm = `%${search}%`;
      params.push(searchTerm, searchTerm, searchTerm);
    }

    // Category filter
    if (category && category !== 'all') {
      query += ' AND category = ?';
      params.push(category);
    }

    // Brand filter
    if (brand) {
      query += ' AND brand = ?';
      params.push(brand);
    }

    // Price range filter
    if (minPrice) {
      query += ' AND price >= ?';
      params.push(parseFloat(minPrice));
    }
    if (maxPrice) {
      query += ' AND price <= ?';
      params.push(parseFloat(maxPrice));
    }

    // Notes filter
    if (notes) {
      const notesList = Array.isArray(notes) ? notes : [notes];
      const notesConditions = notesList.map(() => 'notes LIKE ?').join(' OR ');
      query += ` AND (${notesConditions})`;
      notesList.forEach(note => params.push(`%${note}%`));
    }

    // Sorting
    switch (sortBy) {
      case 'price-low':
        query += ' ORDER BY price ASC';
        break;
      case 'price-high':
        query += ' ORDER BY price DESC';
        break;
      case 'rating':
        query += ' ORDER BY rating DESC';
        break;
      case 'newest':
        query += ' ORDER BY created_at DESC';
        break;
      default:
        query += ' ORDER BY rating DESC, review_count DESC';
    }

    // Pagination
    const offset = (parseInt(page) - 1) * parseInt(limit);
    query += ' LIMIT ? OFFSET ?';
    params.push(parseInt(limit), offset);

    const perfumes = await dbAll(query, params);

    // Parse JSON fields
    const formattedPerfumes = perfumes.map(perfume => ({
      ...perfume,
      notes: JSON.parse(perfume.notes || '[]'),
      sizes: JSON.parse(perfume.sizes || '[]'),
      inStock: Boolean(perfume.in_stock)
    }));

    // Get total count for pagination
    let countQuery = 'SELECT COUNT(*) as total FROM perfumes WHERE 1=1';
    const countParams = params.slice(0, -2); // Remove limit and offset
    
    if (search) {
      countQuery += ' AND (name LIKE ? OR brand LIKE ? OR description LIKE ?)';
    }
    if (category && category !== 'all') {
      countQuery += ' AND category = ?';
    }
    if (brand) {
      countQuery += ' AND brand = ?';
    }
    if (minPrice) {
      countQuery += ' AND price >= ?';
    }
    if (maxPrice) {
      countQuery += ' AND price <= ?';
    }
    if (notes) {
      const notesList = Array.isArray(notes) ? notes : [notes];
      const notesConditions = notesList.map(() => 'notes LIKE ?').join(' OR ');
      countQuery += ` AND (${notesConditions})`;
    }

    const { total } = await dbGet(countQuery, countParams);

    res.json({
      perfumes: formattedPerfumes,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / parseInt(limit))
      }
    });
  } catch (error) {
    console.error('Error fetching perfumes:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get single perfume
router.get('/:id', async (req, res) => {
  try {
    const perfume = await dbGet('SELECT * FROM perfumes WHERE id = ?', [req.params.id]);
    
    if (!perfume) {
      return res.status(404).json({ error: 'Perfume not found' });
    }

    // Parse JSON fields
    const formattedPerfume = {
      ...perfume,
      notes: JSON.parse(perfume.notes || '[]'),
      sizes: JSON.parse(perfume.sizes || '[]'),
      inStock: Boolean(perfume.in_stock)
    };

    res.json(formattedPerfume);
  } catch (error) {
    console.error('Error fetching perfume:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get perfume reviews
router.get('/:id/reviews', async (req, res) => {
  try {
    const reviews = await dbAll(`
      SELECT r.*, u.name as user_name 
      FROM reviews r 
      JOIN users u ON r.user_id = u.id 
      WHERE r.perfume_id = ? 
      ORDER BY r.created_at DESC
    `, [req.params.id]);

    res.json(reviews);
  } catch (error) {
    console.error('Error fetching reviews:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Add review (authenticated)
router.post('/:id/reviews', authenticateToken, async (req, res) => {
  try {
    const { rating, comment } = req.body;
    const perfumeId = req.params.id;
    const userId = req.user.id;

    // Validation
    if (!rating || rating < 1 || rating > 5) {
      return res.status(400).json({ error: 'Rating must be between 1 and 5' });
    }

    // Check if user already reviewed this perfume
    const existingReview = await dbGet(
      'SELECT id FROM reviews WHERE user_id = ? AND perfume_id = ?',
      [userId, perfumeId]
    );

    if (existingReview) {
      return res.status(400).json({ error: 'You have already reviewed this perfume' });
    }

    // Add review
    await dbRun(
      'INSERT INTO reviews (user_id, perfume_id, rating, comment) VALUES (?, ?, ?, ?)',
      [userId, perfumeId, rating, comment]
    );

    // Update perfume rating
    const { avg_rating, review_count } = await dbGet(`
      SELECT AVG(rating) as avg_rating, COUNT(*) as review_count 
      FROM reviews WHERE perfume_id = ?
    `, [perfumeId]);

    await dbRun(
      'UPDATE perfumes SET rating = ?, review_count = ? WHERE id = ?',
      [Math.round(avg_rating * 10) / 10, review_count, perfumeId]
    );

    res.status(201).json({ message: 'Review added successfully' });
  } catch (error) {
    console.error('Error adding review:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get brands
router.get('/meta/brands', async (req, res) => {
  try {
    const brands = await dbAll('SELECT DISTINCT brand FROM perfumes ORDER BY brand');
    res.json(brands.map(b => b.brand));
  } catch (error) {
    console.error('Error fetching brands:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get categories
router.get('/meta/categories', async (req, res) => {
  try {
    const categories = await dbAll('SELECT DISTINCT category FROM perfumes ORDER BY category');
    res.json(categories.map(c => c.category));
  } catch (error) {
    console.error('Error fetching categories:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;