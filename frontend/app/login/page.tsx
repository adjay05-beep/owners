"use client";

import { useState } from 'react';
import { TextInput, PasswordInput, Button, Paper, Title, Container, Text, Alert } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { useRouter } from 'next/navigation';
import { IconAlertCircle } from '@tabler/icons-react';

export default function LoginPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const form = useForm({
        initialValues: {
            username: '',
            password: '',
        },
        validate: {
            username: (value) => (value.length < 2 ? '아이디를 입력해주세요' : null),
            password: (value) => (value.length < 4 ? '비밀번호는 4자 이상입니다' : null),
        },
    });

    const handleSubmit = async (values: typeof form.values) => {
        setLoading(true);
        setError(null);
        try {
            // In Replit/Production, use relative path or env var. For Dev, assuming localhost:8000
            // --- MOCK LOGIN FOR PREVIEW ---
            // Since backend is not running locally, we simulate success
            console.log('Attempting fetch to /api/auth/login...');

            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(values),
                });

                if (res.ok) {
                    const data = await res.json();
                    localStorage.setItem('token', data.access_token);
                } else {
                    console.warn("Backend unavailable, entering Preview Mode");
                    notifications.show({ title: 'Preview Mode', message: '백엔드 연결 실패. 디자인 프리뷰 모드로 진입합니다.', color: 'blue', opacity: 0.9 });
                }
            } catch (err) {
                console.warn("Network Error, entering Preview Mode");
                notifications.show({ title: 'Preview Mode', message: '디자인 데모 모드로 실행됩니다.', color: 'blue' });
            }

            // Always redirect to dashboard for Visual Preview
            setTimeout(() => {
                router.push('/dashboard');
            }, 1000);

        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            background: 'url("https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=2629&auto=format&fit=crop") no-repeat center center fixed',
            backgroundSize: 'cover',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
        }}>
            <Container size={420} my={40}>
                <Paper
                    radius="lg"
                    p={30}
                    style={{
                        background: 'rgba(255, 255, 255, 0.75)',
                        backdropFilter: 'blur(20px)',
                        border: '1px solid rgba(255, 255, 255, 0.3)',
                        boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)'
                    }}
                >
                    <Title ta="center" order={2} style={{ fontWeight: 800, marginBottom: 5 }}>
                        Welcome Back
                    </Title>
                    <Text c="dimmed" size="sm" ta="center" mb={30}>
                        오너스 클럽에 오신 것을 환영합니다
                    </Text>

                    {error && (
                        <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red" mb="md" variant="light">
                            {error}
                        </Alert>
                    )}

                    <form onSubmit={form.onSubmit(handleSubmit)}>
                        <TextInput
                            label="아이디"
                            placeholder="Username"
                            size="md"
                            radius="md"
                            {...form.getInputProps('username')}
                            styles={{ input: { background: 'rgba(255,255,255,0.6)' } }}
                        />
                        <PasswordInput
                            label="비밀번호"
                            placeholder="Password"
                            mt="md"
                            size="md"
                            radius="md"
                            {...form.getInputProps('password')}
                            styles={{ input: { background: 'rgba(255,255,255,0.6)' } }}
                        />

                        <Button fullWidth mt="xl" size="md" radius="md" type="submit" loading={loading}
                            style={{
                                background: 'linear-gradient(45deg, #3B82F6 0%, #2563EB 100%)',
                                boxShadow: '0 4px 14px 0 rgba(0,118,255,0.39)'
                            }}
                        >
                            로그인
                        </Button>
                    </form>

                    <Text ta="center" mt="md" size="sm">
                        계정이 없으신가요?{' '}
                        <Text span c="blue" style={{ cursor: 'pointer', fontWeight: 600 }}>
                            회원가입
                        </Text>
                    </Text>
                </Paper>
            </Container>
        </div>
    );
}
