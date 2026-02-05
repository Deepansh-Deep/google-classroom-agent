'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '../../providers'
import { Loader2 } from 'lucide-react'

export default function AuthCallbackPage() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const { login } = useAuth()

    useEffect(() => {
        const accessToken = searchParams.get('access_token')
        const refreshToken = searchParams.get('refresh_token')
        const error = searchParams.get('error')

        if (error) {
            router.push(`/login?error=${error}`)
            return
        }

        if (accessToken && refreshToken) {
            login(accessToken, refreshToken)
            router.push('/dashboard')
        } else {
            router.push('/login')
        }
    }, [searchParams, login, router])

    return (
        <div className="min-h-screen bg-surface-950 flex items-center justify-center">
            <div className="text-center">
                <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
                <p className="text-surface-400">Completing sign in...</p>
            </div>
        </div>
    )
}
