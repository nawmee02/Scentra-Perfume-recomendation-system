import React, { useState } from 'react';

const ForgotPassword = ({ setActiveSection }) => {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const handleSendOtp = async (e) => {
    e.preventDefault();
    setError('');
    setMsg('');
    const res = await fetch('/api/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (res.ok) {
      setMsg('OTP sent to your email');
      setStep(2);
    } else {
      setError(data.error || 'Error sending OTP');
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    setMsg('');
    const res = await fetch('/api/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, otp, newPassword }),
    });
    const data = await res.json();
    if (res.ok) {
      setMsg('Password reset! You can now log in.');
      setTimeout(() => setActiveSection('login'), 2000);
    } else {
      setError(data.error || 'Error resetting password');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20 max-w-md w-full">
        <h2 className="text-2xl font-bold text-white mb-4">Forgot Password</h2>
        {step === 1 && (
          <form onSubmit={handleSendOtp} className="space-y-4">
            <input
              type="email"
              className="w-full px-4 py-2 rounded bg-white/30 text-black"
              placeholder="Enter your email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
            <button
              type="submit"
              className="w-full bg-amber-500 text-white py-2 rounded"
            >
              Send OTP
            </button>
          </form>
        )}
        {step === 2 && (
          <form onSubmit={handleResetPassword} className="space-y-4">
            <input
              type="text"
              className="w-full px-4 py-2 rounded bg-white/30 text-black"
              placeholder="Enter OTP"
              value={otp}
              onChange={e => setOtp(e.target.value)}
              required
            />
            <input
              type="password"
              className="w-full px-4 py-2 rounded bg-white/30 text-black"
              placeholder="New Password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              required
            />
            <button
              type="submit"
              className="w-full bg-amber-500 text-white py-2 rounded"
            >
              Reset Password
            </button>
          </form>
        )}
        {msg && <div className="text-green-400 mt-4">{msg}</div>}
        {error && <div className="text-red-400 mt-4">{error}</div>}
        <button
          className="mt-4 text-purple-200 underline"
          onClick={() => setActiveSection('login')}
        >
          Back to Login
        </button>
      </div>
    </div>
  );
};

export default ForgotPassword;