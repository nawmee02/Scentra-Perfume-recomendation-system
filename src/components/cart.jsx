import React from 'react';
import { X, Minus, Plus, ShoppingCart } from 'lucide-react';

export default function Cart({ cartItems, onRemove, onQuantityChange, onClose, onCheckout }) {
  const total = cartItems.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );

  return (
    <div className="h-full flex flex-col overflow-y-auto p-4 relative">
      {/* Cross (close) button */}
      <button
        className="absolute top-4 right-4 text-gray-500 hover:text-gray-800 z-10"
        onClick={onClose}
        aria-label="Close cart"
      >
        <X className="w-6 h-6" />
      </button>

      <h2 className="text-2xl font-bold mb-6">Your Cart</h2>

      {cartItems.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full py-16">
          <ShoppingCart className="w-16 h-16 text-purple-300 mb-6" />
          <p className="text-lg font-semibold text-gray-700 mb-2">Your cart is empty!</p>
          <p className="text-gray-500 mb-4 text-center">
            Looks like you haven't added any perfumes yet.<br />
            Discover our exclusive collection and add your favorite scents to the cart.
          </p>
          <span className="text-sm text-purple-500 font-medium">
            “A good fragrance is really a powerful cocktail of memories and emotion.”
          </span>
        </div>
      ) : (
        <div className="space-y-6">
          {cartItems.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between bg-white p-4 rounded-xl shadow"
            >
              <div className="flex items-center space-x-4">
                <img
                  src={item.image_url}
                  alt={item.name}
                  className="w-16 h-16 object-cover rounded"
                />
                <div>
                  <h3 className="font-semibold">{item.name}</h3>
                  <p className="text-sm text-gray-500">{item.brand}</p>
                  <p className="text-sm text-purple-600 font-medium">
                    ${item.price.toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center border rounded px-2 py-1">
                  <button
                    onClick={() => onQuantityChange(item.id, item.quantity - 1)}
                    disabled={item.quantity <= 1}
                    className="text-gray-500 hover:text-gray-800"
                  >
                    <Minus className="w-4 h-4" />
                  </button>
                  <span className="px-3">{item.quantity}</span>
                  <button
                    onClick={() => onQuantityChange(item.id, item.quantity + 1)}
                    className="text-gray-500 hover:text-gray-800"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                <button
                  onClick={() => onRemove(item.id)}
                  className="text-red-500 hover:text-red-700"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {cartItems.length > 0 && (
        <div className="mt-auto pt-6 border-t">
          <p className="text-xl font-semibold text-right">
            Total: <span className="text-purple-600">${total.toFixed(2)}</span>
          </p>
          <button
            className="mt-4 w-full px-6 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
            onClick={onCheckout}
          >
            Checkout
          </button>
        </div>
      )}
    </div>
  );
}
