import React from 'react';
import { Home, Search, Flower2, BookOpen, ShoppingBag, User, LogOut,ShoppingCart } from 'lucide-react';

const Navigation = ({ activeSection, setActiveSection, isLoggedIn, onLogout,cartCount, onCartClick }) => {
    const navItems = [
        { id: 'home', label: 'Home', icon: Home },
        { id: 'perfumefind', label: 'Perfume Find', icon: Search },
        { id: 'notes', label: 'Notes', icon: Flower2 },
        { id: 'blog', label: 'Blog', icon: BookOpen },
        { id: 'buy', label: 'Buy Perfume', icon: ShoppingBag },
        { id: 'cart', label: 'Cart', icon: ShoppingCart }
    ];

    return (
        <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-purple-100">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    <div className="flex items-center space-x-2 cursor-pointer" onClick={() => setActiveSection('home')} title="Go to Home">
                        <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-amber-500 rounded-lg flex items-center justify-center">
                            <Flower2 className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-xl font-bold bg-gradient-to-r from-purple-600 to-amber-500 bg-clip-text text-transparent">
                            Scentra
                        </span>
                    </div>

                    <div className="hidden md:flex items-center space-x-1">
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            return (
                                <button
                                    key={item.id}
                                    onClick={() => {
                                        if (item.id === 'cart') {
                                            onCartClick && onCartClick();
                                        } else {
                                            setActiveSection(item.id);
                                        }
                                    }}
                                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                                        activeSection === item.id
                                            ? 'bg-purple-100 text-purple-700 shadow-sm'
                                            : 'text-gray-600 hover:text-purple-600 hover:bg-purple-50'
                                    }`}
                                >
                                    <Icon className="w-4 h-4" />
                                    <span className="font-medium">{item.label}</span>
                                    {item.id === 'cart' && cartCount > 0 && (
                                        <span className="ml-1 bg-amber-500 text-white text-xs rounded-full px-2 py-0.5">
                                            {cartCount}
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                        {isLoggedIn ? (
                            <>
                                <button
                                    onClick={() => setActiveSection('profile')}
                                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 ${activeSection === 'profile'
                                        ? 'bg-purple-100 text-purple-700 shadow-sm'
                                        : 'text-gray-600 hover:text-purple-600 hover:bg-purple-50'
                                        }`}
                                >
                                    <User className="w-5 h-5" />
                                    <span>Profile</span>
                                </button>
                                <button
                                    onClick={onLogout}
                                    className="flex items-center space-x-2 px-4 py-2 rounded-lg text-gray-600 hover:text-red-600 hover:bg-red-50 transition-all duration-200"
                                >
                                    <LogOut className="w-5 h-5" />
                                    <span>Log Out</span>
                                </button>
                            </>
                        ) : (
                            <button
                                onClick={() => setActiveSection('login')}
                                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 ${activeSection === 'login'
                                    ? 'bg-purple-100 text-purple-700 shadow-sm'
                                    : 'text-gray-600 hover:text-purple-600 hover:bg-purple-50'
                                    }`}
                            >
                                <User className="w-5 h-5" />
                                <span>Log In</span>
                            </button>
                        )}
                        
                    </div>

                    <div className="md:hidden">
                        <button className="p-2 rounded-lg text-gray-600 hover:text-purple-600 hover:bg-purple-50">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </nav>
    );
};

export default Navigation;