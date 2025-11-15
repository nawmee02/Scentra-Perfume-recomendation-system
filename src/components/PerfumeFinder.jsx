import React, { useState, useEffect, useRef } from 'react';

const PerfumeFinder = () => {
    const [messages, setMessages] = useState([
        { role: 'bot', text: "Hi! Describe your ideal scent to get recommendations." }
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;
        const newMessages = [...messages, { role: 'user', text: input }];
        setMessages(newMessages);
        setLoading(true);

        try {
            const res = await fetch('/api/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: input, limit: 5 })
            });
            const { recommendations, error } = await res.json();
            if (error) throw new Error(error);

            const botReply = `Based on your query, these perfumes are recommended:\n${recommendations
             .map((p, i) => `${i + 1}. ${p.name} by ${p.brand}`)
             .join('\n')}`;
            

            setMessages([...newMessages, { role: 'bot', text: botReply }]);
        } catch (err) {
            setMessages([...newMessages, { role: 'bot', text: 'Error fetching recommendations.' }]);
        }

        setLoading(false);
        setInput('');
    };

    return (
        <div className="max-w-xl mx-auto mt-10 bg-white shadow-xl rounded-xl p-6 space-y-4">
            <h2 className="text-2xl font-semibold text-center">🧠 Perfume Chatbot</h2>

            <div className="h-64 overflow-y-auto border p-3 rounded bg-gray-50 space-y-2">
                {messages.map((msg, i) => (
                    <div key={i} className={`text-sm p-2 rounded ${msg.role === 'bot' ? 'bg-blue-100 text-left' : 'bg-green-100 text-right'}`}>
                        <span dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, '<br>') }} />
                    </div>
                ))}
                {loading && <div className="text-sm text-gray-500">Thinking...</div>}
                <div ref={bottomRef} />
            </div>

            <div className="flex gap-2">
                <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSend()}
                    placeholder="Describe your ideal scent..."
                    className="flex-1 border rounded px-3 py-2"
                />
                <button onClick={handleSend} className="bg-blue-600 text-white px-4 py-2 rounded" disabled={loading}>
                    Send
                </button>
            </div>
        </div>
    );
};

export default PerfumeFinder;