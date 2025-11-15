import React, { useState } from "react";

const cities = ["Dhaka", "Chittagong", "Khulna"]; // Example cities
const areas = {
  Dhaka: ["Gulshan", "Banani", "Dhanmondi"],
  Chittagong: ["Pahartali", "Halishahar"],
  Khulna: ["Sonadanga", "Khalishpur"],
};

export default function Checkout({ cartItems = [], onPurchase, onBack, onRemoveFromCart }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    firstName: "",
    lastName: "",
    city: "",
    area: "",
    address: "",
    setDefault: false,
    billToShipping: true,
    updates: true,
    shippingOption: "standard",
    coupon: "",
  });

  const subtotal = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const discount = cartItems.reduce((sum, item) => sum + ((item.original_price ? (item.original_price - item.price) : 0) * item.quantity), 0);
  const vat = +(subtotal * 0.075).toFixed(2);
  const shipping = 0; // You can set based on area/city
  const total = subtotal + vat + shipping;

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
      ...(name === "city" ? { area: "" } : {}),
    }));
  };

  const handlePlaceOrder = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      alert("You must be logged in to place an order.");
      return;
    }
    try {
      const res = await fetch("/api/orders", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          items: cartItems.map(item => ({
            perfumeId: item.id,
            quantity: item.quantity,
            // Optionally add size if you support it: size: item.size
          })),
          shippingAddress: {
            firstName: form.firstName,
            lastName: form.lastName,
            city: form.city,
            area: form.area,
            address: form.address,
          },
          paymentMethod: "cod", // or whatever you want to support
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || "Order failed");
        return;
      }
      // Success: call onPurchase to clear cart and redirect
      if (onPurchase) onPurchase();
      alert("Order placed successfully!");
    } catch (err) {
      alert("Network error. Please try again.");
    }
  };

  return (
    <div className="flex flex-col md:flex-row gap-8 py-8 px-4 max-w-5xl mx-auto">
      {/* Main Form */}
      <div className="flex-1 bg-white rounded-xl shadow-lg p-8">
        {/* Stepper */}
        <div className="flex items-center mb-8">
          <div className={`flex items-center ${step === 1 ? "text-purple-700 font-bold" : "text-gray-400"}`}>
            <span className="w-8 h-8 flex items-center justify-center border-2 border-purple-600 rounded-full mr-2">{step === 1 ? 1 : <span>&#10003;</span>}</span>
            Shipping Information
          </div>
          <div className="flex-1 border-t mx-4 border-gray-300"></div>
          <div className={`flex items-center ${step === 2 ? "text-purple-700 font-bold" : "text-gray-400"}`}>
            <span className="w-8 h-8 flex items-center justify-center border-2 border-purple-600 rounded-full mr-2">{step === 2 ? 2 : ""}</span>
            Payment & Confirmation
          </div>
        </div>

        {step === 1 && (
          <>
            <h2 className="text-xl font-bold mb-4 text-center">SHIPPING INFORMATION</h2>
            <button className="mb-6 w-full bg-black text-white py-2 rounded font-semibold">Add new address</button>
            <form className="space-y-4">
              <div className="flex gap-4">
                <input
                  className="w-1/2 border rounded px-3 py-2"
                  placeholder="First Name"
                  name="firstName"
                  value={form.firstName}
                  onChange={handleChange}
                  required
                />
                <input
                  className="w-1/2 border rounded px-3 py-2"
                  placeholder="Last Name"
                  name="lastName"
                  value={form.lastName}
                  onChange={handleChange}
                  required
                />
              </div>
              <select
                className="w-full border rounded px-3 py-2"
                name="city"
                value={form.city}
                onChange={handleChange}
                required
              >
                <option value="">Select City</option>
                {cities.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <select
                className="w-full border rounded px-3 py-2"
                name="area"
                value={form.area}
                onChange={handleChange}
                required
                disabled={!form.city}
              >
                <option value="">Select Area</option>
                {(areas[form.city] || []).map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Address *"
                name="address"
                value={form.address}
                onChange={handleChange}
                required
              />
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  name="setDefault"
                  checked={form.setDefault}
                  onChange={handleChange}
                />
                <label className="text-sm">Set as default address</label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  name="billToShipping"
                  checked={form.billToShipping}
                  onChange={handleChange}
                />
                <label className="text-sm">Bill to Shipping Address</label>
              </div>
              <div className="my-4">
                <div className="font-semibold mb-2">Shipping Options</div>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="shippingOption"
                    value="standard"
                    checked={form.shippingOption === "standard"}
                    onChange={handleChange}
                  />
                  Standard - 2-7 working days.
                </label>
                <div className="text-xs text-gray-500 ml-6">
                  *Cut off time for shipping: 2:30pm for Standard Delivery, Sunday - Thursday except for holidays.
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  name="updates"
                  checked={form.updates}
                  onChange={handleChange}
                />
                <label className="text-sm">
                  I want to receive updates about offers and events from Scentra
                </label>
              </div>
              <div className="flex justify-between mt-6">
                <button
                  type="button"
                  className="px-6 py-2 rounded bg-gray-200"
                  onClick={onBack}
                >
                  Back
                </button>
                <button
                  type="button"
                  className="px-6 py-2 rounded bg-purple-600 text-white"
                  onClick={() => setStep(2)}
                >
                  Continue
                </button>
              </div>
            </form>
          </>
        )}

        {step === 2 && (
          <div className="text-center">
            <h2 className="text-xl font-bold mb-4">PAYMENT & CONFIRMATION</h2>
            <div className="mb-6 flex flex-col items-center">
              <div className="w-full max-w-md border rounded-lg p-4 mb-4">
                <div className="font-semibold mb-2 text-left">Payment Method</div>
                <label className="flex items-center gap-2 mb-2">
                  <input
                    type="radio"
                    name="paymentMethod"
                    value="cod"
                    checked={form.paymentMethod === "cod"}
                    onChange={e => setForm(f => ({ ...f, paymentMethod: "cod" }))}
                  />
                  Cash On Delivery
                  <span role="img" aria-label="cash">💵</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="paymentMethod"
                    value="sslcommerz"
                    checked={form.paymentMethod === "sslcommerz"}
                    onChange={e => setForm(f => ({ ...f, paymentMethod: "sslcommerz" }))}
                  />
                  Online Payment
                  <img src="https://sslcommerz.com/wp-content/themes/sslcommerz/images/logo.png" alt="SSLCommerz" className="h-5" />
                </label>
              </div>
              <div className="flex items-center gap-2 mb-4">
                <input
                  type="checkbox"
                  checked={form.agree || false}
                  onChange={e => setForm(f => ({ ...f, agree: e.target.checked }))}
                />
                <label className="text-sm">
                  I agree to the <a href="#" className="underline font-semibold">Terms and conditions</a>, <a href="#" className="underline font-semibold">Return & Refund policies</a> and <a href="#" className="underline font-semibold">Privacy Policy</a>
                </label>
              </div>
            </div>
            <button
              className="px-8 py-2 rounded bg-purple-600 text-white font-semibold"
              onClick={() => {
                if (!form.agree) {
                  alert("You must agree to the terms and conditions.");
                  return;
                }
                handlePlaceOrder();
                setStep(3); // Show congratulation card
              }}
              disabled={!form.agree}
            >
              PLACE ORDER
            </button>
            <button
              className="ml-4 px-6 py-2 rounded bg-gray-200"
              onClick={() => setStep(1)}
            >
              Back
            </button>
          </div>
        )}
        {step === 3 && (
          <div className="flex flex-col items-center justify-center min-h-[300px]">
            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <h2 className="text-2xl font-bold text-purple-700 mb-2">Congratulations!</h2>
              <p className="text-gray-700 mb-4">Your order has been placed successfully.</p>
              <button
                className="px-6 py-2 rounded bg-purple-600 text-white font-semibold"
                onClick={onPurchase}
              >
                Go to Home
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Shopping Bag Summary */}
      <div className="w-full md:w-96 bg-white rounded-xl shadow-lg p-6 h-fit">
        <h3 className="text-lg font-bold mb-4">SHOPPING BAG</h3>
        {cartItems.map((item) => (
          <div key={item.id} className="flex items-center mb-4">
            <img src={item.image_url} alt={item.name} className="w-16 h-16 object-cover rounded mr-4" />
            <div className="flex-1">
              <div className="font-semibold">{item.name}</div>
              <div className="text-xs text-gray-500">{item.brand}</div>
              <div className="flex items-center mt-1">
                <span className="text-sm font-medium">{item.sizes ? item.sizes[0] : ""}</span>
                <span className="mx-2">|</span>
                <span className="text-sm">x{item.quantity}</span>
              </div>
            </div>
            <button
              className="ml-2 px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-xs"
              onClick={() => onRemoveFromCart(item.id)}
            >
              Remove
            </button>
            <div className="text-right">
              {item.original_price && item.original_price > item.price && (
                <span className="text-xs bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full mr-1">
                  -{Math.round(100 * (item.original_price - item.price) / item.original_price)}%
                </span>
              )}
              <div className="font-semibold text-purple-700">
                ${(item.price * item.quantity).toLocaleString()}
              </div>
            </div>
          </div>
        ))}
        <div className="border-t pt-4 mt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <span>CART TOTAL</span>
            <span>${subtotal.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span>PRODUCT DISCOUNTS</span>
            <span className="text-green-700">-${discount.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span>SUB TOTAL</span>
            <span>${subtotal.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span>VAT(7.5%)</span>
            <span>${vat.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span>SHIPPING</span>
            <span>
              {shipping === 0 ? (
                <span className="text-gray-400">SELECT LOCATION FOR SHIPPING PRICE</span>
              ) : (
                `$${shipping.toLocaleString()}`
              )}
            </span>
          </div>
          <div className="flex justify-between font-bold text-lg border-t pt-2">
            <span>TOTAL</span>
            <span>${total.toLocaleString()}</span>
          </div>
        </div>
        <form className="mt-4 flex gap-2">
          <input
            type="text"
            placeholder="Coupon Code"
            className="flex-1 border rounded px-3 py-2"
            value={form.coupon}
            name="coupon"
            onChange={handleChange}
          />
          <button
            type="button"
            className="bg-black text-white px-4 rounded"
            // Add coupon logic here
          >
            SUBMIT
          </button>
        </form>
      </div>
    </div>
  );
}