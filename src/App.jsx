import React, { useState, useEffect } from "react";
import Navigation from "./components/Navigation";
import Hero from "./components/Hero";
import PerfumeFinder from "./components/PerfumeFinder";
import Notes from "./components/Notes";
import Blog from "./components/Blog";
import BuyPerfume from "./components/BuyPerfume";
import Login from "./components/Login";
import Profile from "./components/Profile";
import ForgotPassword from './components/ForgotPassword';
import Cart from './components/cart';
import Checkout from './components/Checkout'; 

function App() {
    const [activeSection, setActiveSection] = useState('home');
    const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem("token"));
    const [cart, setCart] = useState([]);
    const [isCartOpen, setIsCartOpen] = useState(false);

    useEffect(() => {
        if (localStorage.getItem("token")) {
            setIsLoggedIn(true);
            setActiveSection('profile');
        }
    }, []);

    const handleLogout = () => {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        setIsLoggedIn(false);
        setActiveSection('login');
    };

    const handleAddToCart = (product) => {
        const existing = cart.find(item => item.id === product.id);
        if (existing) {
            setCart(cart.map(item =>
                item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
            ));
        } else {
            setCart([...cart, { ...product, quantity: 1 }]);
        }
        setIsCartOpen(true);
    };

    const handleRemoveFromCart = (itemId) => {
        setCart(cart.filter(item => item.id !== itemId));
    };

    const handleQuantityChange = (itemId, newQuantity) => {
        setCart(cart.map(item =>
            item.id === itemId ? { ...item, quantity: newQuantity } : item
        ));
    };

    const handleCartIconClick = () => setIsCartOpen(prev => !prev);
    const handleCheckout = () => {setActiveSection('checkout'); setIsCartOpen(false);}; // Handle checkout

    const handleAddToWishlist = async (product) => {
        const token = localStorage.getItem("token");
        if (!token) {
            alert("Please log in to use wishlist.");
            return;
        }
        try {
            const response = await fetch('/api/users/wishlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ perfumeId: product.id }),
            });
            const data = await response.json();
            if (!response.ok) {
                alert(data.error || "Failed to add to wishlist");
                return;
            }
            // Optionally update local wishlist state here
        } catch {
            alert("Error connecting to server");
        }
    };

    const renderSection = () => {
        switch (activeSection) {
            case 'home':
                return <Hero setActiveSection={setActiveSection} />;
            case 'perfumefind':
                return <PerfumeFinder />;
            case 'notes':
                return <Notes />;
            case 'blog':
                return <Blog />;
            case 'buy':
                return <BuyPerfume setActiveSection={setActiveSection} handleAddToCart={handleAddToCart} handleAddToWishlist={handleAddToWishlist} />;
            case 'login':
                return <Login setActiveSection={setActiveSection} setIsLoggedIn={setIsLoggedIn} />;
            case 'profile':
                return <Profile onLogout={handleLogout} handleAddToCart={handleAddToCart} handleAddToWishlist={handleAddToWishlist} />;
            case 'forgot-password':
                return <ForgotPassword setActiveSection={setActiveSection} />;
            case 'checkout':
                return (
                    <Checkout
                        cartItems={cart}
                        onPurchase={() => {
                            setActiveSection('home');
                            setCart([]);
                        }}
                        onBack={() => setActiveSection('home')}
                        onRemoveFromCart={handleRemoveFromCart} // <-- add this line
                    />
                );
            default:
                return <Hero setActiveSection={setActiveSection} />;
        }
    };

    return (
        <div className="relative min-h-screen bg-gradient-to-br from-purple-50 via-white to-amber-50">
            <Navigation
                activeSection={activeSection}
                setActiveSection={setActiveSection}
                isLoggedIn={isLoggedIn}
                onLogout={handleLogout}
                cartCount={cart.reduce((sum, item) => sum + item.quantity, 0)}
                onCartClick={handleCartIconClick}
            />
            <main className="transition-all duration-500 ease-in-out">
                {renderSection()}
            </main>

            {/* Cart Sidebar */}
            <div className={`fixed top-0 right-0 h-full w-80 bg-white shadow-lg z-50 transform transition-transform duration-300 ease-in-out ${isCartOpen ? 'translate-x-0' : 'translate-x-full'}`}>
                <Cart
                    cartItems={cart}
                    onRemove={handleRemoveFromCart}
                    onQuantityChange={handleQuantityChange}
                    onClose={() => setIsCartOpen(false)}
                    onCheckout={() => {
                        setIsCartOpen(false);
                        setActiveSection('checkout'); // <-- use lowercase here
                    }}
                />
            </div>
        </div>
    );
}

export default App;