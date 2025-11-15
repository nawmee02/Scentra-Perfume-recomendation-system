import React from 'react';
import { Search, Sparkles, ArrowRight } from 'lucide-react';

// Accept setActiveSection as a prop
const Hero = ({ setActiveSection }) => {
    return (
        <div className="relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-900 via-purple-800 to-amber-900 opacity-90"></div>

            <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
                <div className="text-center">
                    <div className="flex justify-center mb-8">
                        <div className="flex items-center space-x-2 bg-white/20 backdrop-blur-sm rounded-full px-6 py-3">
                            <Sparkles className="w-5 h-5 text-amber-300" />
                            <span className="text-white font-medium">Discover Your Perfect Scent</span>
                        </div>
                    </div>

                    <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight">
                        Find Your
                        <span className="block bg-gradient-to-r from-amber-300 to-yellow-300 bg-clip-text text-transparent">
                            Signature Fragrance
                        </span>
                    </h1>

                    <p className="text-xl text-purple-100 mb-12 max-w-3xl mx-auto leading-relaxed">
                        Explore thousands of perfumes, discover fragrance notes, and find your perfect scent match
                        with our advanced fragrance finder technology.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
                        <button
                            onClick={() => setActiveSection('perfumefind')}
                            className="group bg-gradient-to-r from-amber-500 to-yellow-500 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:shadow-2xl hover:shadow-amber-500/25 transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2"
                        >
                            <Search className="w-5 h-5" />
                            <span>Find My Perfume</span>
                            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </button>

                        <button
                            onClick={() => setActiveSection('buy')}
                            className="border-2 border-white/30 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:bg-white/10 transition-all duration-300 backdrop-blur-sm"
                        >
                            Browse Collections
                        </button>
                    </div>

                    {/* Feature cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
                        <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 text-center hover:bg-white/20 transition-all duration-300">
                            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <Search className="w-6 h-6 text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Smart Search</h3>
                            <p className="text-purple-100">Find perfumes by notes, brand, occasion, or mood</p>
                        </div>

                        <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 text-center hover:bg-white/20 transition-all duration-300">
                            <div className="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <Sparkles className="w-6 h-6 text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Expert Reviews</h3>
                            <p className="text-purple-100">Read detailed reviews from fragrance experts</p>
                        </div>

                        <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 text-center hover:bg-white/20 transition-all duration-300">
                            <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-teal-500 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <ArrowRight className="w-6 h-6 text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Best Prices</h3>
                            <p className="text-purple-100">Compare prices across top fragrance retailers</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Decorative elements */}
            <div className="absolute top-20 left-10 w-20 h-20 bg-amber-300/20 rounded-full blur-xl"></div>
            <div className="absolute bottom-20 right-10 w-32 h-32 bg-purple-300/20 rounded-full blur-xl"></div>
        </div>
    );
};

export default Hero;
