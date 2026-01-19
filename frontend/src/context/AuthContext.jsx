// frontend/src/context/AuthContext.jsx
import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(null);
    const [username, setUsername] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // On app load, check if we have a token in local storage
        const storedToken = localStorage.getItem('authToken');
        const storedUsername = localStorage.getItem('username');
        
        if (storedToken) {
            setToken(storedToken);
            setUsername(storedUsername);
        }
        setLoading(false);
    }, []);

    // --- THIS IS THE CRITICAL PART ---
    // We ensure this function accepts two separate arguments
    const login = (newToken, newUsername) => {
        console.log("Logging in with:", newToken, newUsername); // Debug log
        
        setToken(newToken);
        setUsername(newUsername);
        
        // Save to LocalStorage so api.js can find it
        localStorage.setItem('authToken', newToken);
        localStorage.setItem('username', newUsername);
    };

    const logout = () => {
        setToken(null);
        setUsername(null);
        localStorage.removeItem('authToken');
        localStorage.removeItem('username');
    };

    const isAuthenticated = !!token;

    return (
        <AuthContext.Provider value={{ token, username, isAuthenticated, login, logout, loading }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    return useContext(AuthContext);
};