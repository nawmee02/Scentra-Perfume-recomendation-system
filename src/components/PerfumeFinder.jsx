import React, { useState, useEffect, useRef } from 'react';

// Renders one perfume as a card: identity, inventory badge, accords, notes,
// and (when present) the reason it matched.
const PerfumeCard = ({ rec, onAddToCart }) => {
    const inStock = rec.in_inventory && rec.in_stock;
    const notes = [rec.top_notes, rec.middle_notes, rec.base_notes].filter(Boolean);
    const reason = rec.rerank_reason || (rec.similarity_reason && rec.similarity_reason.join(' · '));
    return (
        <div className="bg-white border border-purple-100 rounded-lg p-3 shadow-sm h-full flex flex-col justify-between">
            <div>
                <div className="flex items-start justify-between gap-2">
                    <div>
                        <p className="font-semibold text-gray-800 capitalize leading-tight">{rec.name}</p>
                        <p className="text-xs text-gray-500 capitalize">{rec.brand}</p>
                    </div>
                    {rec.in_inventory && (
                        <span className={`shrink-0 text-[11px] px-2 py-0.5 rounded-full font-medium ${
                            inStock ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                        }`}>
                            {inStock ? `In stock${rec.price != null ? ` · $${rec.price}` : ''}` : 'In store'}
                        </span>
                    )}
                </div>

                {rec.accords?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                        {rec.accords.slice(0, 5).map((a, i) => (
                            <span key={i} className="text-[11px] bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full capitalize">{a}</span>
                        ))}
                    </div>
                )}

                {notes.length > 0 && (
                    <p className="text-[11px] text-gray-500 mt-2 capitalize">{notes.join(' · ')}</p>
                )}
                {reason && <p className="text-xs text-gray-600 italic mt-2">{reason}</p>}
            </div>

            {inStock && onAddToCart && (
                <div className="mt-3 pt-2 border-t border-purple-50 flex items-center justify-between">
                    <span className="text-xs font-semibold text-purple-700">
                        {rec.price != null ? `$${rec.price}` : 'Available'}
                    </span>
                    <button
                        onClick={() => onAddToCart({
                            id: rec.frag_id || rec.id,
                            name: rec.name,
                            brand: rec.brand,
                            price: rec.price || 99,
                            image_url: rec.image_url || 'https://images.pexels.com/photos/3685530/pexels-photo-3685530.jpeg?auto=compress&cs=tinysrgb&w=400&h=400&fit=crop',
                            category: rec.accords?.[0] || 'fragrance',
                        })}
                        className="bg-purple-600 hover:bg-purple-700 text-white text-xs px-3 py-1 rounded-md font-medium transition"
                    >
                        Add to Cart
                    </button>
                </div>
            )}
        </div>
    );
};

const EXAMPLES = [
    'sweet vanilla for winter nights',
    'fresh aquatic summer scent',
    'smoky leather for a night out',
    'clean soapy office fragrance',
];

const PerfumeFinder = ({ onAddToCart }) => {
    const [mode, setMode] = useState('search'); // 'search' | 'chat'

    // --- Search (fast, no LLM) ---
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [searched, setSearched] = useState(false);

    const runSearch = async (q) => {
        const term = (q ?? query).trim();
        if (!term) return;
        setQuery(term);
        setSearching(true);
        setSearched(true);
        try {
            const res = await fetch('/api/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: term, limit: 9 })
            });
            const data = await res.json();
            setResults(data.recommendations || []);
        } catch {
            setResults([]);
        }
        setSearching(false);
    };

    // --- Chat (LLM) ---
    const [messages, setMessages] = useState([
        { role: 'bot', reply: "Hi! Describe your ideal scent, or ask for something similar to a fragrance you love." }
    ]);
    const [input, setInput] = useState('');
    const [thinking, setThinking] = useState(false);
    const bottomRef = useRef(null);
    useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;
        const newMessages = [...messages, { role: 'user', reply: input }];
        setMessages(newMessages);
        setThinking(true);
        try {
            const res = await fetch('/api/recommend/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: input, limit: 5 })
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            const recs = data.recommendations || [];
            const reply = data.reply || (recs.length ? 'Here are some matches:' : "I couldn't find a good match — try rephrasing.");
            setMessages([...newMessages, { role: 'bot', reply, recs, offline: data.llm_used === false }]);
        } catch {
            setMessages([...newMessages, { role: 'bot', reply: 'Sorry — the assistant is unavailable right now.' }]);
        }
        setThinking(false);
        setInput('');
    };

    const TabButton = ({ id, label }) => (
        <button
            onClick={() => setMode(id)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
                mode === id ? 'bg-purple-600 text-white' : 'bg-white text-gray-600 border border-purple-200 hover:bg-purple-50'
            }`}
        >{label}</button>
    );

    return (
        <div className="max-w-3xl mx-auto mt-10 bg-gradient-to-b from-purple-50 to-white shadow-xl rounded-xl p-6 space-y-4">
            <h2 className="text-2xl font-semibold text-center text-gray-800">🧠 Scentra Fragrance Finder</h2>

            <div className="flex justify-center gap-2">
                <TabButton id="search" label="🔎 Search" />
                <TabButton id="chat" label="💬 Ask AI" />
            </div>

            {mode === 'search' ? (
                <div className="space-y-4">
                    <div className="flex gap-2">
                        <input
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && runSearch()}
                            placeholder="Describe a scent, mood, notes, or occasion…"
                            className="flex-1 border border-purple-200 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-300"
                        />
                        <button
                            onClick={() => runSearch()}
                            disabled={searching}
                            className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 rounded-lg font-medium disabled:opacity-50"
                        >{searching ? 'Searching…' : 'Search'}</button>
                    </div>

                    {!searched && (
                        <div className="flex flex-wrap gap-2 justify-center">
                            {EXAMPLES.map(ex => (
                                <button key={ex} onClick={() => runSearch(ex)}
                                    className="text-xs text-purple-700 bg-purple-100 hover:bg-purple-200 px-3 py-1 rounded-full">
                                    {ex}
                                </button>
                            ))}
                        </div>
                    )}

                    {searching && <p className="text-center text-sm text-gray-400">Finding fragrances…</p>}
                    {searched && !searching && results.length === 0 && (
                        <p className="text-center text-sm text-gray-400">No matches — try different words.</p>
                    )}

                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {results.map((rec, i) => <PerfumeCard key={i} rec={rec} onAddToCart={onAddToCart} />)}
                    </div>
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="h-96 overflow-y-auto border border-purple-100 p-3 rounded-lg bg-white/60 space-y-3">
                        {messages.map((msg, i) => (
                            <div key={i} className={msg.role === 'user' ? 'text-right' : 'text-left'}>
                                <div className={`inline-block max-w-[90%] text-sm p-2.5 rounded-lg whitespace-pre-line ${
                                    msg.role === 'user' ? 'bg-purple-600 text-white' : 'bg-purple-50 text-gray-800'
                                }`}>
                                    {msg.reply}
                                    {msg.offline && <span className="block text-[10px] text-gray-400 mt-1">offline match (LLM unavailable)</span>}
                                </div>
                                {msg.recs?.length > 0 && (
                                    <div className="mt-2 grid sm:grid-cols-2 gap-2">
                                        {msg.recs.map((rec, j) => <PerfumeCard key={j} rec={rec} onAddToCart={onAddToCart} />)}
                                    </div>
                                )}
                            </div>
                        ))}
                        {thinking && <div className="text-sm text-gray-400">Thinking… (the AI takes ~30-50s)</div>}
                        <div ref={bottomRef} />
                    </div>
                    <div className="flex gap-2">
                        <input
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleSend()}
                            placeholder="e.g. something similar to Dior Sauvage"
                            className="flex-1 border border-purple-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-300"
                        />
                        <button onClick={handleSend} disabled={thinking}
                            className="bg-purple-600 hover:bg-purple-700 text-white px-5 py-2 rounded-lg disabled:opacity-50">
                            Send
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PerfumeFinder;
