import React, { useState } from 'react';
import { Flower2, Leaf, Sparkles, Sun, TreePine, Coffee } from 'lucide-react';

const Notes = () => {
    const fragranceCategories = [
        {
            id: 1,
            name: 'Floral',
            icon: Flower2,
            color: 'from-pink-500 to-rose-500',
            description: 'Delicate and romantic scents featuring flower essences',
            notes: ['Rose', 'Jasmine', 'Lily', 'Peony', 'Tuberose', 'Iris', 'Gardenia', 'Magnolia', 'Freesia', 'Carnation'],
            characteristics: 'Feminine, romantic, soft, and elegant'
        },
        {
            id: 2,
            name: 'Fresh',
            icon: Leaf,
            color: 'from-green-500 to-teal-500',
            description: 'Clean, crisp, and invigorating scents',
            notes: ['Citrus', 'Bergamot', 'Lemon', 'Marine', 'Green Tea', 'Mint', 'Basil', 'Cucumber', 'Eucalyptus', 'Verbena'],
            characteristics: 'Energizing, clean, uplifting, and modern'
        },
        {
            id: 3,
            name: 'Oriental',
            icon: Sparkles,
            color: 'from-amber-500 to-orange-500',
            description: 'Rich, warm, and exotic with spicy undertones',
            notes: ['Amber', 'Vanilla', 'Incense', 'Cinnamon', 'Cardamom', 'Saffron', 'Clove', 'Myrrh', 'Tonka Bean', 'Nutmeg'],
            characteristics: 'Mysterious, sensual, warm, and sophisticated'
        },
        {
            id: 4,
            name: 'Citrus',
            icon: Sun,
            color: 'from-yellow-500 to-orange-400',
            description: 'Bright, zesty, and refreshing fruit-based scents',
            notes: ['Lemon', 'Orange', 'Grapefruit', 'Lime', 'Mandarin', 'Yuzu', 'Bergamot', 'Pomelo', 'Tangerine', 'Kumquat'],
            characteristics: 'Energetic, fresh, bright, and cheerful'
        },
        {
            id: 5,
            name: 'Woody',
            icon: TreePine,
            color: 'from-amber-600 to-brown-500',
            description: 'Warm, dry, and earthy with wood-based notes',
            notes: ['Sandalwood', 'Cedar', 'Rosewood', 'Vetiver', 'Patchouli', 'Oud', 'Mahogany', 'Birch', 'Pine', 'Guaiac Wood'],
            characteristics: 'Grounding, sophisticated, natural, and timeless'
        },
        {
            id: 6,
            name: 'Gourmand',
            icon: Coffee,
            color: 'from-purple-500 to-pink-500',
            description: 'Sweet, edible scents that evoke food and desserts',
            notes: ['Vanilla', 'Chocolate', 'Caramel', 'Coffee', 'Honey', 'Almond', 'Praline', 'Coconut', 'Maple Syrup', 'Toffee'],
            characteristics: 'Comforting, sweet, indulgent, and cozy'
        }
    ];
    const topNotes = [
        { name: 'Bergamot', description: 'Fresh, citrusy, and slightly spicy' },
        { name: 'Lemon', description: 'Bright, zesty, and energizing' },
        { name: 'Rose', description: 'Classic, romantic, and feminine' },
        { name: 'Lavender', description: 'Calming, clean, and herbal' },
    ];

    const middleNotes = [
        { name: 'Jasmine', description: 'Intoxicating, sweet, and floral' },
        { name: 'Geranium', description: 'Green, rosy, and slightly minty' },
        { name: 'Ylang-ylang', description: 'Exotic, creamy, and tropical' },
        { name: 'Cinnamon', description: 'Warm, spicy, and comforting' },
    ];

    const baseNotes = [
        { name: 'Sandalwood', description: 'Creamy, warm, and woody' },
        { name: 'Vanilla', description: 'Sweet, comforting, and gourmand' },
        { name: 'Musk', description: 'Sensual, clean, and animalic' },
        { name: 'Amber', description: 'Warm, resinous, and rich' },
    ];

    const [selectedCategory, setSelectedCategory] = useState(null);
    const [selectedNote, setSelectedNote] = useState(null);

    const noteDetails = {
        Rose: 'Rose is classic, romantic, and feminine, often used in floral perfumes.',
        Jasmine: 'Jasmine is intoxicating, sweet, and floral, adding depth to many scents.',
        Lily: 'Lily is fresh, clean, and elegant, a staple in floral fragrances.',
        Peony: 'Peony is soft, rosy, and slightly fruity, perfect for spring scents.',
        Tuberose: 'Tuberose is creamy, rich, and exotic, used in luxurious perfumes.',
        Iris: 'Iris is powdery, sophisticated, and slightly woody, often in high-end blends.',
        Citrus: 'Citrus notes are bright, zesty, and refreshing, found in fresh scents.',
        Bergamot: 'Bergamot is fresh, citrusy, and slightly spicy, uplifting any fragrance.',
        Lemon: 'Lemon is energizing and clean, a top note in many perfumes.',
        Marine: 'Marine notes evoke the ocean, adding freshness and coolness.',
        'Green Tea': 'Green Tea is calming, fresh, and modern, popular in light fragrances.',
        Mint: 'Mint is cool, crisp, and invigorating, used for freshness.',
        Amber: 'Amber is warm, resinous, and rich, a base for oriental scents.',
        Vanilla: 'Vanilla is sweet, comforting, and gourmand, loved in cozy perfumes.',
        Incense: 'Incense is smoky, mysterious, and spiritual, used in oriental blends.',
        Cinnamon: 'Cinnamon is spicy, warm, and comforting, found in gourmand and oriental scents.',
        Cardamom: 'Cardamom is spicy, aromatic, and slightly sweet, adding complexity.',
        Saffron: 'Saffron is exotic, leathery, and slightly sweet, used in luxury perfumes.',
        Orange: 'Orange is juicy, sweet, and uplifting, a cheerful citrus note.',
        Grapefruit: 'Grapefruit is tart, fresh, and energizing, used in sporty scents.',
        Lime: 'Lime is sharp, zesty, and refreshing, a lively citrus note.',
        Mandarin: 'Mandarin is sweet, soft, and fruity, gentle in citrus blends.',
        Yuzu: 'Yuzu is unique, tart, and aromatic, a Japanese citrus note.',
        Sandalwood: 'Sandalwood is creamy, warm, and woody, a classic base note.',
        Cedar: 'Cedar is dry, woody, and slightly spicy, grounding many perfumes.',
        Rosewood: 'Rosewood is floral, woody, and slightly sweet, used in elegant blends.',
        Vetiver: 'Vetiver is earthy, smoky, and woody, a strong base note.',
        Patchouli: 'Patchouli is earthy, musky, and sweet, found in woody and oriental scents.',
        Oud: 'Oud is rich, smoky, and complex, prized in Middle Eastern perfumery.',
        Chocolate: 'Chocolate is rich, sweet, and indulgent, a gourmand favorite.',
        Caramel: 'Caramel is sweet, buttery, and cozy, used in dessert-like scents.',
        Coffee: 'Coffee is bold, roasted, and energizing, a unique gourmand note.',
        Honey: 'Honey is sweet, warm, and animalic, adding depth and richness.',
        Almond: 'Almond is nutty, sweet, and comforting, found in gourmand blends.',
        Gardenia: 'Creamy, rich white floral with a tropical touch',
        Magnolia: 'Fresh, citrusy-floral with a lemony nuance',
        Freesia: 'Light, airy, and sweet floral with fruity notes',
        Carnation: 'Spicy floral with clove-like undertones',
        Basil: 'Green, herbal, slightly sweet and peppery aroma',
        Cucumber: 'Cool, watery, and refreshing green scent',
        Eucalyptus: 'Sharp, camphorous, and invigorating freshness',
        Verbena: 'Citrusy, lemon-like with a clean green edge',
        Clove: 'Warm, spicy, and slightly woody fragrance',
        Myrrh: 'Resinous, balsamic, and slightly smoky sweetness',
        'Tonka Bean': 'Warm, sweet, with vanilla and almond-like notes',
        Nutmeg: 'Sweet-spicy, warm, and slightly nutty scent',
        Pomelo: 'Bright, citrusy, and mildly sweet grapefruit-like aroma',
        Tangerine: 'Juicy, sweet citrus with a zesty freshness',
        Kumquat: 'Tangy, tart, and slightly sweet citrus character',
        Mahogany: 'Deep, rich, and warm woody fragrance',
        Birch: 'Dry, smoky wood with leathery undertones',
        Pine: 'Fresh, resinous, and crisp evergreen aroma',
        'Guaiac Wood': 'Smoky, tar-like, with subtle sweet woodiness',
        Praline: 'Sweet, nutty, and caramelized gourmand aroma',
        Coconut: 'Creamy, sweet tropical nut aroma',
        'Maple Syrup': 'Rich, sweet, and caramelized sugary scent',
        Toffee: 'Buttery, caramel-like sweetness with warm depth'
    };

    const getNoteImage = (noteName) => {
        const imageMap = {
            Rose: 'https://images.unsplash.com/photo-1586082207282-3dcb61d25ebd?fm=jpg&q=60&w=3000&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8cm9zZSUyMGZsb3dlcnxlbnwwfHwwfHx8MA%3D%3D',
            Jasmine: 'https://cdn.britannica.com/56/197956-050-5062911A/Arabian-jasmine.jpg',
            Lily: 'https://westmountflorist.com/cdn/shop/articles/wf-flower-reference-guide-lily.jpg?v=1697056484&width=2048',
            Peony: 'https://images.pexels.com/photos/931177/pexels-photo-931177.jpeg',
            Tuberose: 'https://m.media-amazon.com/images/I/61XCuEiGIZL._AC_SL1024_.jpg',
            Iris: 'https://www.floraly.com.au/cdn/shop/articles/iris_blog_hero.png?v=1666934661&width=1500',
            Citrus: 'https://cdn.britannica.com/45/190245-050-CCAFE09B/grapefruits-pomelos.jpg',
            Bergamot: 'https://www.bonparfumeur.com/cdn/shop/articles/Bergamote_97431f41-f335-4dca-bff0-997a970098fe.jpg?v=1748259373&width=500',
            Lemon: 'https://images.pexels.com/photos/1414122/pexels-photo-1414122.jpeg',
            Marine: 'https://images.pexels.com/photos/994605/pexels-photo-994605.jpeg',
            'Green Tea': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSo71WCTXj1P3UzC2-Fcc8Fg4QOQQuKikRcmA&s',
            Mint: 'https://nl.lakpura.com/cdn/shop/files/LSZ0075131-01-E.jpg?v=1720184273&width=1946',
            Amber: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTPW9cZelLuwZbIhElH1tb0xEeVkcGQs2N5-w&s',
            Vanilla: 'https://images.pexels.com/photos/3640637/pexels-photo-3640637.jpeg',
            Incense: 'https://images.pexels.com/photos/3639806/pexels-photo-3639806.jpeg?auto=compress&cs=tinysrgb&dpr=1&w=500',
            Cinnamon: 'https://m.media-amazon.com/images/I/41WS+MBBU5L._UF894,1000_QL80_.jpg',
            Cardamom: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSvUve1VGJbcVsOL6nzEupAppvo0KyGcE3FBw&s',
            Saffron: 'https://media.post.rvohealth.io/wp-content/uploads/2020/11/saffron-732x549-thumbnail.jpg',
            Orange: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT-6GoLpPXoOkT0lAuFcxXwJSQ7nxtRQqVJLg&s',
            Grapefruit: 'https://t3.ftcdn.net/jpg/05/58/80/62/360_F_558806247_KIVBvDJs19mYesCFHWk3TueoOrjegzlp.jpg',
            Lime: 'https://images.pexels.com/photos/109275/pexels-photo-109275.jpeg',
            Mandarin: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTRf9QHhGo6PJmgcXeav1r7xtpNIIQrfl1Z8g&s',
            Yuzu: 'https://www.paperandtea.com/cdn/shop/articles/Yuzu-Frucht_b9c63327-39f8-4909-9593-786de0e0dcbd.jpg?v=1754575654&width=1500',
            Sandalwood: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSsFBuwngS6dm2ZVvFFznbx9jD5c2liF-qn-A&s',
            Cedar: 'https://treecompany.ca/cdn/shop/files/red_cedar_3.jpg?v=1738701850',
            Rosewood: 'https://media.istockphoto.com/id/1622987198/photo/wood-logs-of-siam-rosewood-exotic-wooden-beautiful-pattern-for-crafts.jpg?s=612x612&w=0&k=20&c=dNzExTvRBXu_CB4iGAJ9i8TCtr2-qSICxUgkIpdTBE4=',
            Vetiver: 'https://media.istockphoto.com/id/1356727657/vector/vector-drawing-vetiver-plant.jpg?s=612x612&w=0&k=20&c=pNBTpSMrzQirt1OjFY-QHSmm7g_Ync9UJpXA5rarlk0=',
            Patchouli: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ_BN8zReHXpzpOYudf7A6idLTojCt59qDn-Q&s',
            Oud: 'https://indicanaoud.com/cdn/shop/articles/Agarwood_Oud_from_Assam_India_2048x.jpg?v=1712742893',
            Chocolate: 'https://images.pexels.com/photos/2067396/pexels-photo-2067396.jpeg',
            Caramel: 'https://www.whitakerschocolates.com/cdn/shop/articles/Who-Invented-Caramel.jpg?v=1715958777',
            Coffee: 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg',
            Honey: 'https://astorapiaries.com/cdn/shop/articles/AA_How_to_tell_teh_difference_between_good_and_bad_honey_1080x.png?v=1686662686',
            Almond: 'https://images.pexels.com/photos/57042/pexels-photo-57042.jpeg',
            Gardenia: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQSDUzdkZIZpye7ER0IRy3naqHcN6I01cFsNJdXHAVMXodzP7pOgq6JXFP1NqI0o-OPnL-biz3R3WoKFILNmsXcrw',
            Magnolia: 'https://www.arborday.org/sites/arborday.org/files/styles/blog_hero_image/public/migration_uploads/southern-magnolia-iStock-596767820.jpg.webp',
            Freesia: 'https://www.gardenia.net/wp-content/uploads/2023/05/Freesia-Double-Blue.webp',
            Carnation: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTccqrwNQ8STgjjnYfivmkqVCVhletnhyFkNg&s',
            Basil: 'https://gardeningsg.nparks.gov.sg/images/Plants/ThaiBasil_JacChua%20(1).jpg',
            Cucumber: 'https://cdn.apartmenttherapy.info/image/upload/v1718217356/stock/shutterstock_127158479.jpg',
            Eucalyptus: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRyv-gUSHBmKoS9T3JDAQ4GqepG8i3bl8Y8Fg&s',
            Verbena: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQP7qW95kpHtwrKhdJIwCKjOLtwP7DpmeDiGA&s',
            Clove: 'https://cdn.mos.cms.futurecdn.net/dD52bNpiVsDi4fPkGFB6bL.jpg',
            Myrrh: 'https://www.lvnea.com/cdn/shop/files/Myrrh.jpg?v=1742391443&width=1445',
            'Tonka Bean': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ03sJFPn6hzqYpeE_PFcaFMrLpPDs0DUnRUA&s',
            Nutmeg: 'https://cdn.britannica.com/77/170777-050-3A754B3D/Nutmeg-seeds-ground-spice.jpg',
            Pomelo: 'https://www.diet-health.info/images/recipes/700/pomelo-by-insjoy-fotolia-170282407.jpg',
            Tangerine: 'https://b2963128.smushcdn.com/2963128/wp-content/uploads/2022/11/Tangerine-800x675.jpg?lossy=1&strip=1&webp=1',
            Kumquat: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Kumquat_from_Spain.jpg/960px-Kumquat_from_Spain.jpg',
            Mahogany: 'https://rukminim2.flixcart.com/image/850/1000/kvtuxe80/plant-seed/q/b/u/80-swetania-mahogany-80per-packet-green-india-original-imag8mtkus5btwgk.jpeg?q=90&crop=false',
            Birch: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTHAKZyt_nr0r96fmck-N3nZWRqKeI5Qc752g&s',
            Pine: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQfiri3k2FPo3YS2Nxwo2NAfVqZ0hRLGsO2Aw&s',
            'Guaiac Wood': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTDA4fVVrjMM_0Vjj3pwMpQZvjJ0d1cwb_7Zw&s',
            Praline: 'https://www.biggerbolderbaking.com/wp-content/uploads/2018/11/BAS209-Homemade-Praline-Thumbnail-FINAL-NO-COPY-500x500.jpg',
            Coconut: 'https://images.squarespace-cdn.com/content/v1/5c1074accc8fed6a4251da8f/1652200437658-RFWI16B6LU8U3BF7ZN9V/shutterstock_490174816.jpg',
            'Maple Syrup': 'https://caramelandcashews.com/wp-content/uploads/2023/08/spicy-maple-syrup-5-1-of-1.jpg',
            Toffee: 'https://www.allrecipes.com/thmb/CYepGDVzW15Q-rBIZkmxr_IonLk=/1500x0/filters:no_upscale():max_bytes(150000):strip_icc()/73412-best-toffee-ever-super-easy-mfs445-1-f0be2d4a336f42468eccd45bdecf5f94.jpg'


        

        };
        
        return imageMap[noteName] || 'https://images.pexels.com/photos/1020728/pexels-photo-1020728.jpeg';
    };

    const getCategoryBackground = (categoryName) => {
        const backgrounds = {
            Floral: 'https://images.unsplash.com/photo-1527061011665-3652c757a4d4',
            Fresh: 'https://images.unsplash.com/photo-1505118380757-91f5f5632de0',
            Oriental: 'https://images.unsplash.com/photo-1519730722595-a5ff788dea4d',
            Woody: 'https://static.vecteezy.com/system/resources/thumbnails/066/479/500/small/up-wood-picture-photo.jpg',
            Gourmand: 'https://images.unsplash.com/photo-1484723091739-30a097e8f929',
            Citrus: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSlDPbIS_7b_NHII6faqpeJ9q5t1pAywqpt3g&s'
        };
        return backgrounds[categoryName] || 'https://images.unsplash.com/photo-1519730722595-a5ff788dea4d';
    };

    const gradientMap = {
         Rose: 'from-pink-50 via-rose-50 to-pink-100',
        Jasmine: 'from-yellow-50 via-green-50 to-lime-100',
        Lily: 'from-blue-50 via-white to-blue-100',
        Peony: 'from-pink-100 via-rose-100 to-pink-200',
        Tuberose: 'from-rose-50 via-pink-50 to-white',
        Iris: 'from-purple-50 via-indigo-50 to-white',
        Gardenia: 'from-green-50 via-white to-pink-50',
        Magnolia: 'from-yellow-50 via-pink-50 to-white',
        Freesia: 'from-purple-50 via-pink-50 to-yellow-50',
        Carnation: 'from-red-50 via-pink-50 to-white',
        Basil: 'from-green-100 via-lime-50 to-white',
        Cucumber: 'from-green-50 via-blue-50 to-white',
        Eucalyptus: 'from-green-200 via-gray-50 to-white',
        Verbena: 'from-yellow-100 via-green-50 to-white',
        Clove: 'from-brown-100 via-red-50 to-white',
        Myrrh: 'from-amber-100 via-yellow-50 to-white',
        'Tonka Bean': 'from-brown-100 via-yellow-50 to-white',
        Nutmeg: 'from-orange-100 via-brown-50 to-white',
        Pomelo: 'from-yellow-100 via-orange-50 to-white',
        Tangerine: 'from-orange-100 via-yellow-100 to-white',
        Kumquat: 'from-orange-200 via-yellow-50 to-white',
        Mahogany: 'from-brown-200 via-amber-100 to-white',
        Birch: 'from-gray-200 via-white to-green-50',
        Pine: 'from-green-200 via-brown-50 to-white',
        'Guaiac Wood': 'from-brown-200 via-gray-100 to-white',
        Praline: 'from-amber-100 via-brown-50 to-white',
        Coconut: 'from-yellow-50 via-brown-50 to-white',
        'Maple Syrup': 'from-amber-200 via-yellow-50 to-white',
        Toffee: 'from-amber-100 via-brown-50 to-white'
    };

    if (selectedCategory && selectedNote) {
        const note = noteDetails[selectedNote];
        const Icon = selectedCategory.icon;
        const gradient = gradientMap[selectedNote] || 'from-pink-50 via-white to-amber-50';
        const imgSrc = getNoteImage(selectedNote);

        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-purple-100 via-white to-amber-100">
                <button
                    className="mb-8 px-5 py-2 bg-gradient-to-r from-gray-200 to-gray-300 rounded-full shadow hover:from-gray-300 hover:to-gray-400 text-gray-700 font-semibold"
                    onClick={() => setSelectedNote(null)}
                >
                    ← Back to Common Notes
                </button>
                <div
                    className={`rounded-3xl shadow-2xl p-10 flex flex-col items-center w-full max-w-md bg-opacity-95 relative overflow-hidden bg-gradient-to-br ${gradient}`}
                    style={{ 
                        backgroundImage: `linear-gradient(135deg, rgba(255,255,255,0.7) 0%, rgba(255,255,255,0.9) 60%, rgba(255,255,255,0.7) 100%), url('${imgSrc}')`, 
                        backgroundBlendMode: 'overlay', 
                        backgroundSize: 'cover', 
                        backgroundPosition: 'center' 
                    }}
                >
                    <div className="absolute inset-0 bg-white bg-opacity-40 pointer-events-none" />
                    <div className="relative z-10 flex flex-col items-center w-full">
                        <h2 className="text-3xl font-extrabold text-gray-900 mb-6 tracking-tight text-center">{selectedNote}</h2>
                        <p className="text-lg text-gray-700 text-center mb-4">{note}</p>
                        <div className="flex gap-2 mt-4">
                            <span className="px-3 py-1 bg-white bg-opacity-70 rounded-full text-sm font-medium text-gray-700 shadow-sm">
                                {selectedCategory.name}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (selectedCategory) {
        const Icon = selectedCategory.icon;
        const bgImage = getCategoryBackground(selectedCategory.name);

        return (
            <div
                className="min-h-screen flex flex-col items-center justify-center bg-cover bg-center"
                style={{ backgroundImage: `url(${bgImage})` }}
            >
                <div className="absolute inset-0 bg-white bg-opacity-45 z-0" />
                <button
                    className="mb-8 px-5 py-2 bg-gradient-to-r from-gray-200 to-gray-300 rounded-full shadow hover:from-gray-300 hover:to-gray-400 text-gray-700 font-semibold z-10"
                    onClick={() => setSelectedCategory(null)}
                >
                    ← Back
                </button>
                <div className="bg-white rounded-3xl shadow-2xl p-10 flex flex-col items-center w-full max-w-md z-10">
                    <div className={`w-20 h-20 mb-6 bg-gradient-to-br ${selectedCategory.color} rounded-full flex items-center justify-center shadow-lg`}>
                        <Icon className="w-10 h-10 text-white" />
                    </div>
                    <h2 className="text-4xl font-extrabold text-gray-900 mb-6 tracking-tight text-center">{selectedCategory.name}</h2>
                    <p className="text-lg text-gray-600 mb-6 text-center">{selectedCategory.description}</p>
                    <h4 className="text-xl font-semibold text-gray-800 mb-4 text-center">Common Notes</h4>
                    <div className="flex flex-wrap justify-center gap-3">
                        {selectedCategory.notes.map(note => {
                            const imgSrc = getNoteImage(note);
                            return (
                                <button
                                    key={note}
                                    className="px-4 py-2 bg-gradient-to-r from-purple-200 to-amber-200 text-gray-900 text-base rounded-full font-medium shadow flex items-center gap-2 transform transition duration-300 hover:scale-110 hover:bg-gradient-to-r hover:from-amber-200 hover:to-purple-200 focus:outline-none"
                                    type="button"
                                    onClick={() => setSelectedNote(note)}
                                >
                                    <img 
                                        src={imgSrc} 
                                        alt={note} 
                                        className="w-6 h-6 object-cover rounded-full" 
                                        onError={(e) => {
                                            e.target.onerror = null; 
                                            e.target.src = 'https://images.pexels.com/photos/1020728/pexels-photo-1020728.jpeg';
                                        }}
                                    />
                                    {note}
                                </button>
                            );
                        })}
                    </div>
                    <div className="mt-8 w-full">
                        <h4 className="text-xl font-semibold text-gray-800 mb-2 text-center">Characteristics</h4>
                        <p className="text-gray-600 text-center">{selectedCategory.characteristics}</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div className="text-center mb-16">
                <h1 className="text-4xl font-bold text-gray-900 mb-4">
                    Understanding Fragrance Notes
                </h1>
                <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                    Discover the art of perfumery through fragrance families, notes, and the science behind scent composition
                </p>
            </div>

            <div className="mb-16">
                <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">Fragrance Families</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {fragranceCategories.map(category => {
                        const Icon = category.icon;
                        return (
                            <button
                                key={category.id}
                                className="bg-white rounded-2xl shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300 transform hover:scale-105 text-left w-full focus:outline-none"
                                onClick={() => setSelectedCategory(category)}
                            >
                                <div className={`h-32 bg-gradient-to-br ${category.color} flex items-center justify-center`}>
                                    <Icon className="w-12 h-12 text-white" />
                                </div>
                                <div className="p-6">
                                    <h3 className="text-2xl font-bold text-gray-900 mb-3">{category.name}</h3>
                                    <p className="text-gray-600 mb-4">{category.description}</p>
                                    <div className="mb-2">
                                        <span className="font-semibold text-gray-900">Common Notes: </span>
                                        <span className="text-gray-700 text-sm">{category.notes.join(', ')}</span>
                                    </div>
                                    <div>
                                        <h4 className="font-semibold text-gray-900 mb-2">Characteristics:</h4>
                                        <p className="text-gray-600 text-sm">{category.characteristics}</p>
                                    </div>
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>

            <div className="mb-16">
                <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">The Fragrance Pyramid</h2>
                <div className="bg-white rounded-2xl shadow-lg p-8">
                    <div className="text-center mb-8">
                        <p className="text-lg text-gray-600">
                            Every perfume is composed of three layers of notes that unfold over time
                        </p>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="text-center">
                            <div className="w-24 h-24 bg-gradient-to-br from-yellow-400 to-orange-400 rounded-full flex items-center justify-center mx-auto mb-6">
                                <span className="text-white font-bold text-lg">TOP</span>
                            </div>
                            <h3 className="text-2xl font-bold text-gray-900 mb-4">Top Notes</h3>
                            <p className="text-gray-600 mb-6">The initial impression, lasting 15-30 minutes</p>
                            <div className="space-y-3">
                                {topNotes.map(note => (
                                    <div key={note.name} className="bg-yellow-50 rounded-lg p-3">
                                        <h4 className="font-semibold text-gray-900">{note.name}</h4>
                                        <p className="text-sm text-gray-600">{note.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="text-center">
                            <div className="w-24 h-24 bg-gradient-to-br from-pink-400 to-purple-400 rounded-full flex items-center justify-center mx-auto mb-6">
                                <span className="text-white font-bold text-lg">HEART</span>
                            </div>
                            <h3 className="text-2xl font-bold text-gray-900 mb-4">Heart Notes</h3>
                            <p className="text-gray-600 mb-6">The main body, lasting 2-4 hours</p>
                            <div className="space-y-3">
                                {middleNotes.map(note => (
                                    <div key={note.name} className="bg-purple-50 rounded-lg p-3">
                                        <h4 className="font-semibold text-gray-900">{note.name}</h4>
                                        <p className="text-sm text-gray-600">{note.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="text-center">
                            <div className="w-24 h-24 bg-gradient-to-br from-amber-600 to-brown-500 rounded-full flex items-center justify-center mx-auto mb-6">
                                <span className="text-white font-bold text-lg">BASE</span>
                            </div>
                            <h3 className="text-2xl font-bold text-gray-900 mb-4">Base Notes</h3>
                            <p className="text-gray-600 mb-6">The foundation, lasting 6+ hours</p>
                            <div className="space-y-3">
                                {baseNotes.map(note => (
                                    <div key={note.name} className="bg-amber-50 rounded-lg p-3">
                                        <h4 className="font-semibold text-gray-900">{note.name}</h4>
                                        <p className="text-sm text-gray-600">{note.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="bg-gradient-to-br from-purple-50 to-amber-50 rounded-2xl p-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-6 text-center">Pro Tips for Fragrance Lovers</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-white rounded-lg p-6 shadow-sm">
                        <h3 className="text-xl font-semibold text-gray-900 mb-3">How to Test Perfumes</h3>
                        <ul className="space-y-2 text-gray-600">
                            <li>• Test on clean skin, not on paper strips</li>
                            <li>• Wait 30 minutes to smell the heart notes</li>
                            <li>• Test only 2-3 fragrances at once</li>
                            <li>• Don't rub your wrists together</li>
                        </ul>
                    </div>
                    <div className="bg-white rounded-lg p-6 shadow-sm">
                        <h3 className="text-xl font-semibold text-gray-900 mb-3">Application Tips</h3>
                        <ul className="space-y-2 text-gray-600">
                            <li>• Apply to pulse points (wrists, neck, behind ears)</li>
                            <li>• Spray from 6 inches away</li>
                            <li>• Layer with matching body products</li>
                            <li>• Store in cool, dark places</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Notes;
