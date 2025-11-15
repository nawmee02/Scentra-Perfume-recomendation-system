import React, { useState } from 'react';
import { Calendar, User, Clock, ArrowRight, Heart } from 'lucide-react';

const Blog = () => {
    const featuredPost = {
        id: 1,
        title: 'The Art of Layering Fragrances: A Complete Guide',
        excerpt: 'Master the sophisticated technique of fragrance layering to create your own unique scent signature that reflects your personality.',
        author: 'Arman Hossain Nawmee',
        date: '2025-01-15',
        readTime: '8 min read',
        category: 'Technique',
        image: 'https://www.hausofgloi.com/cdn/shop/articles/layering_2fe1fc47-ffaa-43a4-9c01-71137bd71daa_1200x1200.jpg?v=1582564387',
        featured: true,
        content: `Full Article:  
Layering fragrances is a sophisticated technique that allows you to create a scent that is uniquely yours. Rather than relying on a single perfume, layering involves combining two or more fragrances to craft a personalized aroma that reflects your mood, personality, or even the occasion. This art form has been practiced for centuries in the Middle East and is now gaining popularity worldwide among fragrance enthusiasts.

 Why Layer Fragrances?

Layering offers several benefits:
- Personalization: You can create a signature scent that no one else has.
- Versatility: Adjust your fragrance to suit different seasons, events, or times of day.
- Depth and Longevity: Layering can add complexity and help your scent last longer.

 How to Start Layering

1. Begin with Clean Skin: 
   Always start with freshly showered skin. Unscented moisturizers can help lock in fragrance and provide a base for layering.

2. Choose Your Scents:
   Select perfumes that share complementary notes. For beginners, stick to two fragrances. Common combinations include:
   - Floral + Citrus (for freshness)
   - Woody + Spicy (for warmth)
   - Gourmand + Vanilla (for sweetness)
   - Musk + Anything (for depth)

3. Apply in the Right Order:
   Start with the heavier, richer scent as your base, then add the lighter fragrance on top. This helps the lighter notes shine while the base provides longevity.

4. Spray Strategically: 
   You can spray both scents on the same pulse points (wrists, neck, behind ears) or layer them on different parts of your body for a more subtle blend.

5. Experiment and Adjust:
   Don’t be afraid to try different combinations. Sometimes, unexpected pairings create the most memorable results.

 Pro Tips for Successful Layering

- Test Before You Commit:
  Try layering on a small patch of skin before applying all over.
- Stick to the Same Family:
  If you’re unsure, layer scents from the same fragrance family (e.g., all florals or all orientals).
- Use Unscented Products:  
  Start with unscented lotions or oils to avoid clashing with your chosen perfumes.
- Less is More:
  Don’t overdo it. Two to three sprays of each fragrance are usually enough.

Layering with Other Products

You can also layer by using matching or complementary scented body washes, lotions, and hair mists. Many brands offer fragrance lines with multiple products designed for layering.

 Common Mistakes to Avoid

- Mixing Too Many Scents: 
  Stick to two or three fragrances to avoid an overwhelming result.
- Ignoring Seasonality: 
  Heavy, spicy scents may be too much for summer, while light florals might not last in winter.
- Not Considering Your Environment:
  Some environments (like the office) call for subtlety, while evenings out allow for bolder combinations.

Final Thoughts

The art of layering fragrances is all about creativity and self-expression. There are no strict rules—just guidelines to help you discover what works best for you. With a little experimentation, you’ll find combinations that make you feel confident, unique, and unforgettable.

Ready to create your signature scent? Start layering and let your fragrance tell your story!
`
    };

    const blogPosts = [
        {
            id: 2,
            title: 'Top 10 Sustainable Perfume Brands to Watch in 2025',
            excerpt: 'Discover eco-friendly fragrance houses leading the way in sustainable luxury perfumery.',
            author: 'Arman Hossain Nawmee',
            date: '2025-01-12',
            readTime: '6 min read',
            category: 'Sustainability',
            image: 'https://energytheory.com/wp-content/uploads/2024/03/best-non-toxic-perfume-brands-1.png',
            content: `10 Sustainable Perfume Brands to Watch in 2025

As the fragrance industry evolves, sustainability has become a cornerstone of innovation. In 2025, discerning consumers are gravitating towards perfume brands that prioritize natural ingredients, ethical sourcing, and eco-friendly packaging. Here's a curated list of 10 sustainable perfume brands making significant strides in the industry:

1. Abel

Renowned for its commitment to 100% natural ingredients, Abel offers fragrances that are both luxurious and eco-conscious. Their minimalist packaging and vegan formulations make them a top choice for sustainability enthusiasts.

2. Floral Street

Based in London, Floral Street combines vibrant floral notes with a strong commitment to sustainability. Their vegan and cruelty-free perfumes are housed in recyclable packaging, reflecting their dedication to the environment.

3. By Rosie Jane

This brand emphasizes clean beauty by offering fragrances made from natural ingredients. Their minimalist approach extends to packaging, using recyclable materials to minimize environmental impact.

4. Maison Louis Marie

Maison Louis Marie blends botanical elements with sophisticated scents. Their use of sustainable ingredients and commitment to cruelty-free practices make them a standout in the eco-luxury market.

5. Ellis Brooklyn

Ellis Brooklyn offers modern, complex scents while prioritizing sustainability. Their fragrances are housed in recyclable packaging, and they focus on using clean ingredients to create luxurious experiences.

6. DedCool

DedCool is known for its unisex, clean, and sustainable fragrances. Their commitment to non-toxic ingredients and eco-friendly packaging aligns with the growing demand for ethical beauty products.

7. Flora & Fauna

This brand offers organic perfumes crafted from natural ingredients. Their dedication to sustainability is evident in their use of eco-friendly packaging and ethical sourcing practices.

8. Abbott Fragrances

Abbott Fragrances creates scents inspired by nature, using sustainable ingredients and packaging. Their commitment to conservation and environmental responsibility sets them apart in the fragrance industry.

9. Bastille

A French fragrance house, Bastille offers perfumes that blend liberty and sustainability. Their use of natural ingredients and commitment to eco-friendly practices make them a noteworthy brand in 2025.

10. The Nature of Things

Based in Dublin, The Nature of Things focuses on high-quality, ethically sourced essential oils. Their wellness products, including perfumes, emphasize environmental sustainability and consumer connection to natural fragrances.

Conclusion
The fragrance industry in 2025 is witnessing a transformative shift towards sustainability. Brands like Abel, Floral Street, and Maison Louis Marie are leading the way by offering luxurious scents crafted with ethical practices and eco-friendly packaging. As consumers become more environmentally conscious, these brands exemplify how luxury and sustainability can harmoniously coexist.`
        },
        {
            id: 3,
            title: 'Fragrance Chemistry: Understanding How Perfumes Work',
            excerpt: 'Dive deep into the science behind how fragrances interact with your skin and environment.',
            author: 'Arman Hossain Nawmee',
            date: '2025-01-10',
            readTime: '10 min read',
            category: 'Science',
            image: 'https://cdn.shopify.com/s/files/1/0608/9418/3561/files/blog8.jpg?v=1714046198',
            content: `

Perfumes have fascinated humans for thousands of years, offering an invisible yet powerful way to express personality, evoke memories, and influence mood. Behind their enchanting aromas lies a complex interplay of chemistry, biology, and artistry. Understanding fragrance chemistry not only reveals how perfumes work but also provides insight into why some scents linger while others fade away.

The Building Blocks of Perfumes

Perfumes are composed of a mixture of volatile compounds known as aromatic molecules. These molecules can be natural, derived from flowers, fruits, spices, or woods, or synthetic, crafted in a lab to mimic or enhance natural scents. Each perfume is typically built around three layers, called notes:

Top Notes: These are the first scents you perceive upon application. They are usually light, fresh, and volatile, evaporating quickly. Examples include citrus, mint, or light florals.

Middle Notes (Heart Notes): These emerge as the top notes fade and form the main character of the fragrance. Common heart notes are rose, jasmine, and lavender.

Base Notes: These are the foundation, providing depth and longevity. Base notes are often rich, heavy molecules such as musk, amber, sandalwood, or vanilla, and they linger for hours.

The careful blending of these notes is what gives a perfume its unique personality and progression over time.

How Fragrance Molecules Interact with Our Senses

Perfumes work by stimulating the olfactory receptors in the nose. When aromatic molecules enter the nasal cavity, they bind to specialized proteins called olfactory receptors, which send signals to the brain. The brain then interprets these signals as distinct scents. Interestingly, humans can detect thousands of different molecules, and combinations of them can create an almost infinite range of fragrances.

The interaction between scent molecules and our receptors is highly specific. Some molecules may trigger pleasant memories, while others may evoke discomfort. This is why the emotional impact of perfume can be profound.

The Role of Volatility and Solubility

The evaporation rate of fragrance molecules determines how quickly different notes are perceived. Top notes evaporate fastest due to their high volatility, while base notes are less volatile and last longer on the skin.

Perfumes are usually formulated in a solvent, most commonly ethanol, which helps dissolve fragrance molecules and allows them to disperse evenly when sprayed. The alcohol also aids in evaporation, carrying the scent molecules into the air and onto your skin.

Fixatives: Making Scents Last

One challenge in perfume chemistry is controlling longevity. Without intervention, many aromatic molecules would evaporate too quickly. To counter this, perfumers use fixatives, which are compounds that slow the evaporation of more volatile molecules. Natural fixatives include resins and woods, while synthetic fixatives can be engineered for specific purposes. Fixatives help ensure that the perfume evolves gracefully from top to base notes over hours.

Modern Advances in Fragrance Chemistry

Modern fragrance chemistry has expanded far beyond traditional plant extracts. Innovations include:

Molecular design: Creating entirely new scent molecules not found in nature.

Encapsulation: Embedding fragrance molecules in microcapsules to control release over time.

Sustainable chemistry: Using eco-friendly and renewable sources to produce perfumes, reducing reliance on endangered plants and synthetic chemicals with high environmental impact.

These advances allow perfumers to craft more intricate, longer-lasting, and environmentally responsible fragrances.

Conclusion

Perfume is more than just a pleasant smell—it is a sophisticated interplay of chemistry, biology, and art. By understanding how aromatic molecules interact with our senses, how volatility shapes fragrance progression, and how fixatives enhance longevity, we can better appreciate the science behind our favorite scents. Whether natural or synthetic, every perfume is a miniature chemical symphony designed to enchant the senses and evoke emotion.`
        },
        {
            id: 4,
            title: 'Seasonal Scents: Choosing the Perfect Fragrance for Every Season',
            excerpt: 'Learn how to select fragrances that complement the changing seasons and weather.',
            author: 'Arman Hossain Nawmee',
            date: '2025-01-08',
            readTime: '5 min read',
            category: 'Lifestyle',
            image: 'https://www.nisarabeauty.com/cdn/shop/articles/Blog_Image_4_875caecc-a49f-4af8-9747-4ebd1b3f4065.jpg?v=1714204334',
            content: `Seasonal Scents: Choosing the Perfect Fragrance for Every Season

A great fragrance doesn’t just smell good—it feels right for the time and place. Just as we switch wardrobes and foods with the seasons, perfumes too have a rhythm that aligns with weather, mood, and occasions. Choosing the right fragrance for each season can enhance your presence, evoke the perfect ambiance, and leave a lasting impression.

Spring: Fresh and Floral

Spring is a season of renewal and blossoming. Light, airy, and floral scents dominate this time, reflecting nature’s rebirth. Think of notes like:

Floral: Jasmine, lily of the valley, peony

Green: Fresh grass, leaves, herbs

Fruity: Pear, apple, or soft citrus

Spring fragrances are generally light to moderate in intensity, perfect for daytime wear. They evoke freshness, optimism, and gentle energy, making them ideal for outdoor activities and casual settings.

Summer: Crisp and Citrusy

Summer calls for perfumes that are refreshing and vibrant, cutting through the heat with clean, zesty aromas. Key summer notes include:

Citrus: Lemon, bergamot, grapefruit

Aquatic: Sea breeze, marine notes

Tropical fruits: Pineapple, mango, coconut

High temperatures can intensify scents, so light, eau de toilette or cologne concentrations are preferred. Summer perfumes often lean toward bright and invigorating, providing a cooling effect and a sense of energy.

Autumn: Warm and Spicy

Autumn evokes cozy, rich, and comforting vibes. Fragrances for this season are usually warm, deep, and slightly sweet, complementing the turning leaves and crisp air. Common autumn notes are:

Spices: Cinnamon, clove, nutmeg

Woody: Cedarwood, sandalwood, vetiver

Resins & Gourmand: Vanilla, amber, tonka bean

These scents work beautifully in evenings or cooler weather, creating a sense of intimacy and sophistication.

Winter: Deep and Intense

Winter fragrances are bold and enveloping, perfect for combating the chill. They are typically long-lasting and intense, often combining rich woods, spices, and gourmand notes. Popular winter notes include:

Oriental & Amber: Patchouli, frankincense, myrrh

Woody: Oakmoss, oud, sandalwood

Gourmand: Chocolate, caramel, coffee

Winter perfumes exude warmth and luxury, making them ideal for formal events, holiday gatherings, or cozy nights indoors.

Tips for Choosing Seasonal Fragrances

Consider temperature: Lighter scents suit warmer months; heavier scents complement colder months.

Think about longevity: Warm weather can amplify fragrance, so don’t over-apply in summer.

Layer carefully: Combine perfumes with body lotions or oils for a more nuanced effect.

Experiment: Fragrance is personal—try seasonal scents and notice how they interact with your skin chemistry.

Conclusion

Matching a fragrance to the season isn’t just about smelling nice—it’s about harmonizing with the environment and your mood. From the fresh florals of spring to the deep, spicy woods of winter, seasonal perfumes allow you to express yourself uniquely and feel perfectly in tune with the world around you. By paying attention to notes, intensity, and temperature, you can make every scent a reflection of the season and a subtle extension of your personality.`
        },
        {
            id: 5,
            title: 'Vintage Perfumes: A Journey Through Fragrance History',
            excerpt: 'Explore iconic fragrances from past decades and their lasting impact on modern perfumery.',
            author: 'Arman Hossain Nawmee',
            date: '2025-01-05',
            readTime: '7 min read',
            category: 'History',
            image: 'https://www.carrementbelle.com/blog/wp-content/uploads/2019/12/history-perfume-19thcentury.jpg',
            content: `Vintage Perfumes: A Journey Through Fragrance History

Perfumes are more than just a pleasant aroma—they are a reflection of culture, artistry, and personal expression. Vintage perfumes, in particular, offer a glimpse into the evolving tastes, trends, and techniques of different eras. Exploring these classic scents is like taking a journey through time, revealing not only the history of fragrance but also the stories of the people who wore them.

The Origins of Perfume

Perfume has existed for thousands of years, with origins tracing back to ancient civilizations:

Egypt: Perfumes were used in religious rituals and burial ceremonies. Aromatic oils like frankincense, myrrh, and lotus were highly prized.

Greece and Rome: Perfumes became a part of daily life, used in baths, cosmetics, and social rituals. The Romans introduced complex blending techniques.

Middle Ages and Renaissance: Perfumes were essential in masking odors and signified status among the elite. Flower-based and herb-based scents became popular.

Each period influenced the creation of fragrances, leading to the birth of what we now consider vintage perfumes.

What Makes a Perfume “Vintage”?

A vintage perfume is typically one that was produced in the past and is either discontinued, reformulated, or crafted using traditional methods no longer common today. Key characteristics include:

Original Formulation: Older perfumes often contain natural ingredients in higher concentrations, giving them richer and more complex profiles.

Distinctive Character: Vintage fragrances reflect the olfactory trends of their time, from powdery florals of the 1920s to bold orientals of the 1970s.

Collectibility: Vintage bottles and packaging often carry historical and aesthetic value, making them prized among collectors.

Owning a vintage perfume is like holding a piece of history—a scent that tells the story of a particular era.

Iconic Eras in Perfume History

1920s–1930s: The Golden Age of Classic Florals

Scent Profile: Powdery, floral, and sophisticated

Examples: Chanel No. 5 (original formula), Guerlain Shalimar

1940s–1950s: Post-War Elegance

Scent Profile: Rich florals and aldehydes, designed to convey glamour and femininity

Examples: Dior Miss Dior, Caron Bellodgia

1960s–1970s: Bold and Experimental

Scent Profile: Spicy, oriental, and exotic; experimentation with synthetic ingredients

Examples: Yves Saint Laurent Opium, Givenchy Amarige

1980s–1990s: Power and Statement

Scent Profile: Strong, assertive, often heavy florals and amber

Examples: Calvin Klein Obsession, Lancôme Trésor

Why Vintage Perfumes Are Unique

Vintage perfumes often have qualities that modern fragrances can’t replicate:

Higher Concentration of Natural Ingredients: Many older perfumes relied more on essential oils rather than synthetics, giving a warmer and more nuanced scent.

Complexity and Longevity: Natural ingredients tend to evolve differently on the skin, offering a richer olfactory journey.

Historical Charm: Vintage perfumes carry the essence of the era they were created in, offering a nostalgic experience that modern scents rarely provide.

Caring for Vintage Perfumes

Preserving vintage perfumes requires care:

Store in a Cool, Dark Place: Heat, light, and humidity degrade fragrances over time.

Avoid Frequent Air Exposure: Keep bottles tightly sealed to prevent oxidation.

Check Expiration: Even vintage perfumes have shelf lives; natural oils can change or fade after decades.

Conclusion

Vintage perfumes are more than just fragrances—they are a window into history, capturing the culture, innovation, and artistry of their time. From the opulent florals of the early 20th century to the bold orientals of the 1970s, these timeless scents continue to captivate collectors and enthusiasts. Wearing a vintage perfume is not just about smelling beautiful; it’s about connecting with the stories, emotions, and memories embedded in every drop.`
        },
        {
            id: 6,
            title: 'Building Your Fragrance Wardrobe: Essential Scents for Every Occasion',
            excerpt: 'Create a versatile collection of perfumes suitable for work, play, and special occasions.',
            author: 'Arman Hossain Nawmee',
            date: '2025-01-03',
            readTime: '6 min read',
            category: 'Guide',
            image: 'https://images.pexels.com/photos/965989/pexels-photo-965989.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop',
            content: `**Full Article:**  
A well-rounded fragrance wardrobe includes scents for different occasions and moods. Consider having a fresh, clean scent for work, a romantic floral for evenings out, and a deep, woody fragrance for special occasions...`
        },
        {
            id: 7,
            title: 'The Psychology of Scent: How Fragrance Affects Mood and Memory',
            excerpt: 'Discover the powerful connection between scent, emotions, and psychological well-being.',
            author: 'Arman Hossain Nawmee',
            date: '2025-01-01',
            readTime: '9 min read',
            category: 'Psychology',
            image: 'https://blog.lafco.com/wp-content/uploads/2023/01/woman-smelling-flowers.jpg',
            content: `**Full Article:**  
Scent has a unique ability to evoke memories and influence emotions. This article explores the science behind scent perception and offers insights into how you can use fragrance to enhance your mood and well-being...`
        }
    ];

    const categories = [
        { name: 'All', count: 12 },
        { name: 'Reviews', count: 8 },
        { name: 'Technique', count: 5 },
        { name: 'Sustainability', count: 3 },
        { name: 'Science', count: 4 },
        { name: 'Lifestyle', count: 6 },
        { name: 'History', count: 2 },
    ];

    const [selectedPost, setSelectedPost] = useState(null);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            {!selectedPost ? (
                <>
                    <div className="text-center mb-16">
                        <h1 className="text-4xl font-bold text-gray-900 mb-4">
                            Fragrance Blog
                        </h1>
                        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                            Discover the latest trends, expert reviews, and insider knowledge from the world of perfumery
                        </p>
                    </div>

                    {/* Featured Post */}
                    <div className="mb-16">
                        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
                            <div className="lg:flex">
                                <div className="lg:w-1/2">
                                    <img
                                        src={featuredPost.image}
                                        alt={featuredPost.title}
                                        className="w-full h-64 lg:h-full object-cover"
                                    />
                                </div>
                                <div className="lg:w-1/2 p-8 lg:p-12">
                                    <div className="flex items-center mb-4">
                                        <span className="bg-gradient-to-r from-purple-600 to-purple-700 text-white px-3 py-1 rounded-full text-sm font-medium">
                                            Featured
                                        </span>
                                        <span className="ml-3 text-purple-600 font-medium">{featuredPost.category}</span>
                                    </div>

                                    <h2 className="text-3xl font-bold text-gray-900 mb-4 leading-tight">
                                        {featuredPost.title}
                                    </h2>

                                    <p className="text-gray-600 mb-6 text-lg leading-relaxed">
                                        {featuredPost.excerpt}
                                    </p>

                                    <div className="flex items-center mb-6 text-gray-500 text-sm">
                                        <User className="w-4 h-4 mr-2" />
                                        <span className="mr-4">{featuredPost.author}</span>
                                        <Calendar className="w-4 h-4 mr-2" />
                                        <span className="mr-4">{new Date(featuredPost.date).toLocaleDateString()}</span>
                                        <Clock className="w-4 h-4 mr-2" />
                                        <span>{featuredPost.readTime}</span>
                                    </div>

                                    <button
                                        className="group bg-gradient-to-r from-purple-600 to-purple-700 text-white px-8 py-3 rounded-xl font-semibold hover:shadow-lg transition-all duration-200 flex items-center space-x-2"
                                        onClick={() => setSelectedPost(featuredPost)}
                                    >
                                        <span>Read Article</span>
                                        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="lg:flex lg:space-x-12">
                        {/* Main Content */}
                        <div className="lg:w-2/3">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                {blogPosts.map(post => (
                                    <article
                                        key={post.id}
                                        className="group bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300 transform hover:scale-105 cursor-pointer"
                                        onClick={() => setSelectedPost(post)}
                                    >
                                        <div className="aspect-w-16 aspect-h-9 overflow-hidden">
                                            <img
                                                src={post.image}
                                                alt={post.title}
                                                className="w-full h-48 object-cover group-hover:scale-110 transition-transform duration-300"
                                            />
                                        </div>

                                        <div className="p-6">
                                            <div className="flex items-center justify-between mb-3">
                                                <span className="text-purple-600 font-medium text-sm">{post.category}</span>
                                                <button className="text-gray-400 hover:text-red-500 transition-colors">
                                                    <Heart className="w-4 h-4" />
                                                </button>
                                            </div>

                                            <h3 className="text-xl font-bold text-gray-900 mb-3 line-clamp-2 group-hover:text-purple-600 transition-colors">
                                                {post.title}
                                            </h3>

                                            <p className="text-gray-600 mb-4 line-clamp-3">
                                                {post.excerpt}
                                            </p>

                                            <div className="flex items-center justify-between text-gray-500 text-sm">
                                                <div className="flex items-center space-x-4">
                                                    <span className="flex items-center">
                                                        <User className="w-3 h-3 mr-1" />
                                                        {post.author}
                                                    </span>
                                                    <span className="flex items-center">
                                                        <Clock className="w-3 h-3 mr-1" />
                                                        {post.readTime}
                                                    </span>
                                                </div>
                                                <span>{new Date(post.date).toLocaleDateString()}</span>
                                            </div>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        </div>

                        {/* Sidebar */}
                        <div className="lg:w-1/3 mt-12 lg:mt-0">
                            {/* Categories */}
                            <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
                                <h3 className="text-xl font-bold text-gray-900 mb-4">Categories</h3>
                                <div className="space-y-2">
                                    {categories.map(category => (
                                        <button
                                            key={category.name}
                                            className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-purple-50 transition-colors text-left"
                                        >
                                            <span className="text-gray-700 hover:text-purple-600">{category.name}</span>
                                            <span className="text-gray-400 text-sm">({category.count})</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Newsletter */}
                            <div className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-xl p-6 text-white">
                                <h3 className="text-xl font-bold mb-3">Stay Updated</h3>
                                <p className="mb-4 text-purple-100">
                                    Get the latest fragrance news, reviews, and exclusive content delivered to your inbox.
                                </p>
                                <div className="space-y-3">
                                    <input
                                        type="email"
                                        placeholder="Enter your email"
                                        className="w-full px-4 py-2 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-purple-300"
                                    />
                                    <button className="w-full bg-white text-purple-600 px-4 py-2 rounded-lg font-semibold hover:bg-purple-50 transition-colors">
                                        Subscribe
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            ) : (
                // Single blog post view
                <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-3xl mx-auto">
                    <button
                        className="mb-4 text-purple-600 hover:underline"
                        onClick={() => setSelectedPost(null)}
                    >
                        ← Back to Blog
                    </button>
                    <img src={selectedPost.image} alt={selectedPost.title} className="w-full h-64 object-cover rounded-xl mb-6" />
                    <h2 className="text-3xl font-bold mb-4">{selectedPost.title}</h2>
                    <div className="flex items-center mb-4 text-gray-500 text-sm">
                        <span className="mr-4">{selectedPost.author}</span>
                        <span className="mr-4">{new Date(selectedPost.date).toLocaleDateString()}</span>
                        <span>{selectedPost.readTime}</span>
                    </div>
                    <div className="prose max-w-none whitespace-pre-line">{selectedPost.content}</div>
                </div>
            )}
        </div>
    );
}


export default Blog;