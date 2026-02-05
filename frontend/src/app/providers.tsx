'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, createContext, useContext, useEffect } from 'react'

// Auth context
interface User {
    id: string
    email: string
    name: string
    role: 'admin' | 'teacher' | 'student'
    avatar_url?: string
}

interface AuthContextType {
    user: User | null
    token: string | null
    login: (token: string, refreshToken: string) => void
    logout: () => void
    isLoading: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) throw new Error('useAuth must be used within AuthProvider')
    return context
}

// Theme context
interface ThemeContextType {
    theme: 'light' | 'dark'
    toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | null>(null)

export function useTheme() {
    const context = useContext(ThemeContext)
    if (!context) throw new Error('useTheme must be used within ThemeProvider')
    return context
}

export function Providers({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 60 * 1000,
                retry: 1,
            },
        },
    }))

    const [user, setUser] = useState<User | null>(null)
    const [token, setToken] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [theme, setTheme] = useState<'light' | 'dark'>('dark')

    useEffect(() => {
        // Load from localStorage
        const storedToken = localStorage.getItem('access_token')
        const storedUser = localStorage.getItem('user')
        const storedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null

        if (storedToken && storedUser) {
            setToken(storedToken)
            setUser(JSON.parse(storedUser))
        }
        if (storedTheme) {
            setTheme(storedTheme)
            document.documentElement.classList.toggle('dark', storedTheme === 'dark')
        } else {
            document.documentElement.classList.add('dark')
        }
        setIsLoading(false)
    }, [])

    const login = (newToken: string, refreshToken: string) => {
        localStorage.setItem('access_token', newToken)
        localStorage.setItem('refresh_token', refreshToken)
        setToken(newToken)

        // Fetch user info
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${newToken}` }
        })
            .then(res => res.json())
            .then(userData => {
                setUser(userData)
                localStorage.setItem('user', JSON.stringify(userData))
            })
    }

    const logout = () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        setToken(null)
        setUser(null)
    }

    const toggleTheme = () => {
        const newTheme = theme === 'light' ? 'dark' : 'light'
        setTheme(newTheme)
        localStorage.setItem('theme', newTheme)
        document.documentElement.classList.toggle('dark', newTheme === 'dark')
    }

    return (
        <QueryClientProvider client={queryClient}>
            <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
                <ThemeContext.Provider value={{ theme, toggleTheme }}>
                    {children}
                </ThemeContext.Provider>
            </AuthContext.Provider>
        </QueryClientProvider>
    )
}
