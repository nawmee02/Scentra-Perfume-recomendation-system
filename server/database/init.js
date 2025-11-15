import sqlite3 from 'sqlite3';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DB_PATH = join(__dirname, 'perfume_finder.db');

// Create database connection
export const db = new sqlite3.Database(DB_PATH);

// Promisify database methods
export const dbRun = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function(err) {
      if (err) reject(err);
      else resolve({ id: this.lastID, changes: this.changes });
    });
  });
};

export const dbGet = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
};

export const dbAll = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
};

// Initialize database tables
export async function initializeDatabase() {
  try {
    // Users table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        avatar TEXT,
        favourite_Scent TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Perfumes table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS perfumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        brand TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        original_price DECIMAL(10,2),
        description TEXT,
        category TEXT NOT NULL,
        notes TEXT, -- JSON string of fragrance notes
        sizes TEXT, -- JSON string of available sizes
        image_url TEXT,
        rating DECIMAL(3,2) DEFAULT 0,
        review_count INTEGER DEFAULT 0,
        in_stock BOOLEAN DEFAULT 1,
        discount INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Blog posts table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS blog_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        excerpt TEXT,
        content TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT NOT NULL,
        image_url TEXT,
        read_time TEXT,
        featured BOOLEAN DEFAULT 0,
        published BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Orders table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        status TEXT DEFAULT 'pending',
        shipping_address TEXT,
        payment_method TEXT,
        payment_status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
      )
    `);

    // Order items table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        perfume_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        size TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (perfume_id) REFERENCES perfumes (id)
      )
    `);

    // Reviews table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        perfume_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        comment TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (perfume_id) REFERENCES perfumes (id)
      )
    `);

    // Wishlist table
    await dbRun(`
      CREATE TABLE IF NOT EXISTS wishlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        perfume_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (perfume_id) REFERENCES perfumes (id),
        UNIQUE(user_id, perfume_id)
      )
    `);

    // Insert sample data
    await insertSampleData();
    
    console.log('Database tables created successfully');
  } catch (error) {
    console.error('Error initializing database:', error);
    throw error;
  }
}

async function insertSampleData() {
  try {
    // Check if data already exists
    const existingPerfumes = await dbGet('SELECT COUNT(*) as count FROM perfumes');
    if (existingPerfumes.count > 0) {
      return; // Data already exists
    }

    // Sample perfumes
    const perfumes = [
      {
        name: 'Chanel No. 5 Eau de Parfum',
        brand: 'Chanel',
        price: 150,
        original_price: 180,
        description: 'The legendary fragrance that defines timeless elegance and sophistication.',
        category: 'floral',
        notes: JSON.stringify(['Aldehydes', 'Rose', 'Jasmine', 'Sandalwood', 'Vanilla']),
        sizes: JSON.stringify(['50ml', '100ml', '200ml']),
        image_url: 'https://www.chanel.com/images//t_one//w_0.51,h_0.51,c_crop/q_auto:good,f_autoplus,fl_lossy,dpr_1.1/w_1020/n-5-eau-de-parfum-spray-1-7fl-oz--packshot-default-125430-9564912484382.jpg',
        rating: 4.8,
        review_count: 1250,
        discount: 17
      },
      {
        name: 'Tom Ford Black Orchid',
        brand: 'Tom Ford',
        price: 185,
        original_price: 220,
        description: 'A luxurious and sensual fragrance with rich, dark accords.',
        category: 'oriental',
        notes: JSON.stringify(['Black Truffle', 'Ylang-Ylang', 'Black Orchid', 'Patchouli', 'Vanilla']),
        sizes: JSON.stringify(['50ml', '100ml']),
        image_url: 'https://images.pexels.com/photos/1190297/pexels-photo-1190297.jpeg?auto=compress&cs=tinysrgb&w=400&h=400&fit=crop',
        rating: 4.6,
        review_count: 890,
        discount: 16
      },
      {
        name: 'Creed Aventus',
        brand: 'Creed',
        price: 350,
        original_price: 385,
        description: 'The ultimate masculine fragrance celebrating strength and success.',
        category: 'woody',
        notes: JSON.stringify(['Pineapple', 'Bergamot', 'Birch', 'Musk', 'Oakmoss']),
        sizes: JSON.stringify(['50ml', '100ml', '250ml']),
        image_url: 'https://fragrancebd.com/wp-content/uploads/2021/05/Creed-Aventus-100mL.jpg',
        rating: 4.9,
        review_count: 2100,
        discount: 9
      },
      {
        name: 'Dior Sauvage Eau de Parfum',
        brand: 'Dior',
        price: 98,
        original_price: 120,
        description: 'Wild and authentic, capturing the essence of wide-open spaces.',
        category: 'fresh',
        notes: JSON.stringify(['Bergamot', 'Pepper', 'Lavender', 'Ambroxan', 'Cedar']),
        sizes: JSON.stringify(['60ml', '100ml', '200ml']),
        image_url: 'https://images.pexels.com/photos/3685530/pexels-photo-3685530.jpeg?auto=compress&cs=tinysrgb&w=400&h=400&fit=crop',
        rating: 4.7,
        review_count: 1680,
        discount: 18
      },
      {
        name: 'YSL Black Opium',
        brand: 'Yves Saint Laurent',
        price: 120,
        original_price: 145,
        description: 'Addictive and mysterious, a modern twist on the classic oriental.',
        category: 'gourmand',
        notes: JSON.stringify(['Coffee', 'Vanilla', 'White Flowers', 'Cedar', 'Patchouli']),
        sizes: JSON.stringify(['50ml', '90ml', '150ml']),
        image_url: 'https://images.pexels.com/photos/1961796/pexels-photo-1961796.jpeg?auto=compress&cs=tinysrgb&w=400&h=400&fit=crop',
        rating: 4.5,
        review_count: 1420,
        in_stock: 0,
        discount: 17
      },
      {
        name: 'Gucci Bloom Eau de Parfum',
        brand: 'Gucci',
        price: 108,
        original_price: 130,
        description: 'A rich white floral fragrance that captures the spirit of authentic femininity.',
        category: 'floral',
        notes: JSON.stringify(['Jasmine', 'Tuberose', 'Rangoon Creeper', 'Sandalwood']),
        sizes: JSON.stringify(['50ml', '100ml']),
        image_url: 'https://images.pexels.com/photos/3685532/pexels-photo-3685532.jpeg?auto=compress&cs=tinysrgb&w=400&h=400&fit=crop',
        rating: 4.4,
        review_count: 756,
        discount: 17
      }
    ];

    for (const perfume of perfumes) {
      await dbRun(`
        INSERT INTO perfumes (name, brand, price, original_price, description, category, notes, sizes, image_url, rating, review_count, in_stock, discount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [
        perfume.name, perfume.brand, perfume.price, perfume.original_price, perfume.description,
        perfume.category, perfume.notes, perfume.sizes, perfume.image_url, perfume.rating,
        perfume.review_count, perfume.in_stock ?? 1, perfume.discount
      ]);
    }
 
    // Sample blog posts
    const blogPosts = [
      {
        title: 'The Art of Layering Fragrances: A Complete Guide',
        excerpt: 'Master the sophisticated technique of fragrance layering to create your own unique scent signature that reflects your personality.',
        content: 'Fragrance layering is an art form that allows you to create a unique scent signature...',
        author: 'Arman Hossain Nawmee',
        category: 'Technique',
        image_url: 'https://images.pexels.com/photos/3685530/pexels-photo-3685530.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&fit=crop',
        read_time: '8 min read',
        featured: 1
      },
      {
        title: 'Top 10 Sustainable Perfume Brands to Watch in 2024',
        excerpt: 'Discover eco-friendly fragrance houses leading the way in sustainable luxury perfumery.',
        content: 'Sustainability in perfumery is becoming increasingly important...',
        author: 'Emma Chen',
        category: 'Sustainability',
        image_url: 'https://images.pexels.com/photos/1190297/pexels-photo-1190297.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop',
        read_time: '6 min read',
        featured: 0
      }
    ];

    for (const post of blogPosts) {
      await dbRun(`
        INSERT INTO blog_posts (title, excerpt, content, author, category, image_url, read_time, featured)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `, [post.title, post.excerpt, post.content, post.author, post.category, post.image_url, post.read_time, post.featured]);
    }

    console.log('Sample data inserted successfully');
  } catch (error) {
    console.error('Error inserting sample data:', error);
  }
}

// Remove or comment out these lines after the columns are added once:
// await dbRun(`ALTER TABLE users ADD COLUMN reset_otp TEXT`);
// await dbRun(`ALTER TABLE users ADD COLUMN reset_otp_expiry INTEGER`);