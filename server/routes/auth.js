import express from 'express';
import bcrypt from 'bcryptjs';
import { dbRun, dbGet } from '../database/init.js';
import { generateToken, authenticateToken } from '../middleware/auth.js';
import nodemailer from 'nodemailer';

const router = express.Router();

// Register
router.post('/register', async (req, res) => {
  try {
    const { name, email, password } = req.body;

    // Validation
    if (!name || !email || !password) {
      return res.status(400).json({ error: 'All fields are required' });
    }

    if (password.length < 6) {
      return res.status(400).json({ error: 'Password must be at least 6 characters' });
    }

    // Check if user exists
    const existingUser = await dbGet('SELECT id FROM users WHERE email = ?', [email]);
    if (existingUser) {
      return res.status(400).json({ error: 'User already exists with this email' });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Create user
    const result = await dbRun(
      'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
      [name, email, hashedPassword]
    );

    // Generate token
    const token = generateToken(result.id);

    res.status(201).json({
      message: 'User created successfully',
      token,
      user: {
        id: result.id,
        name,
        email,
        role: 'user'
      }
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Login
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    // Validation
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' });
    }

    // Find user
    const user = await dbGet('SELECT * FROM users WHERE email = ?', [email]);
    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Check password
    const isValidPassword = await bcrypt.compare(password, user.password);
    if (!isValidPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Generate token
    const token = generateToken(user.id);

    res.json({
      message: 'Login successful',
      token,
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get current user
router.get('/me', authenticateToken, (req, res) => {
  res.json({ user: req.user });
});

// Logout (client-side token removal)
router.post('/logout', authenticateToken, (req, res) => {
  res.json({ message: 'Logout successful' });
});

// Send OTP for password reset
router.post('/forgot-password', async (req, res) => {
  const { email } = req.body;
  if (!email) return res.status(400).json({ error: 'Email required' });

  const user = await dbGet('SELECT * FROM users WHERE email = ?', [email]);
  if (!user) return res.status(404).json({ error: 'No user with that email' });

  // Generate OTP and expiry
  const otp = Math.floor(100000 + Math.random() * 900000).toString();
  const otpExpiry = Date.now() + 15 * 60 * 1000; // 15 minutes

  await dbRun(
    'UPDATE users SET reset_otp = ?, reset_otp_expiry = ? WHERE id = ?',
    [otp, otpExpiry, user.id]
  );

  // Send OTP via email (configure your SMTP in .env)
  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  });

  await transporter.sendMail({
    from: process.env.SMTP_USER,
    to: email,
    subject: 'Your Scentra Password Reset OTP',
    text: `Your OTP is: ${otp}`,
  });

  res.json({ message: 'OTP sent to email' });
});

// Reset password with OTP
router.post('/reset-password', async (req, res) => {
  const { email, otp, newPassword } = req.body;
  if (!email || !otp || !newPassword)
    return res.status(400).json({ error: 'All fields required' });

  const user = await dbGet('SELECT * FROM users WHERE email = ?', [email]);
  if (!user || !user.reset_otp || !user.reset_otp_expiry)
    return res.status(400).json({ error: 'Invalid request' });

  if (user.reset_otp !== otp)
    return res.status(400).json({ error: 'Invalid OTP' });

  if (Date.now() > Number(user.reset_otp_expiry))
    return res.status(400).json({ error: 'OTP expired' });

  const hashedPassword = await bcrypt.hash(newPassword, 10);

  await dbRun(
    'UPDATE users SET password = ?, reset_otp = NULL, reset_otp_expiry = NULL WHERE id = ?',
    [hashedPassword, user.id]
  );

  res.json({ message: 'Password reset successful' });
});

export default router;