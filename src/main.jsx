import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { BrowserRouter } from "react-router-dom";  // import router

ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
        <BrowserRouter>   {/* wrap App with BrowserRouter */}
            <App />
        </BrowserRouter>
    </React.StrictMode>
);
