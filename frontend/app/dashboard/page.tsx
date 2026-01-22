"use client";

import { Container, SimpleGrid, Paper, Text, Group, Badge, Button, ThemeIcon, Progress, Grid, Title, RingProgress } from '@mantine/core';
import { IconMessageChatbot, IconChartBar, IconMapPin, IconPencil, IconTruckDelivery, IconChevronRight, IconTrendingUp } from '@tabler/icons-react';

export default function Dashboard() {
    // Mock Data
    const progress = 85;

    return (
        <Container size="md" py="xl" style={{ paddingBottom: 80 }}>
            {/* HEADER */}
            <div style={{ marginBottom: 30 }}>
                <Title order={2}>안녕하세요, 김사장님! 👋</Title>
                <Text c="dimmed">오늘도 매장 성장을 위해 달려볼까요?</Text>
            </div>

            {/* 1. SUPER CARD (Status) */}
            <Paper p="xl" radius="lg" style={{
                background: 'linear-gradient(135deg, #F0F7FF 0%, #FFFFFF 100%)', // Slightly more distinct bg
                border: '1px solid #DCE9F5',
                marginBottom: 30,
                boxShadow: '0 8px 30px rgba(0,0,0,0.08)' // Stronger shadow
            }}>
                <Text c="blue.7" fw={800} fz="sm" tt="uppercase" mb={5}>Today's Briefing</Text>
                <Title order={3} mb="md" style={{ fontSize: '1.75rem' }}>내 매장 진단 점수는 <span style={{ color: '#228BE6' }}>{progress}점</span> 입니다.</Title>
                <Text c="#495057" size="md" fw={500} mb="xl" style={{ maxWidth: 500, lineHeight: 1.6 }}>
                    상위 10% 매장이 되기까지 얼마 남지 않았어요! <br />
                    오늘 추천드리는 액션을 확인하고 점수를 올려보세요.
                </Text>

                <Group>
                    <Paper radius="md" p="sm" withBorder style={{ display: 'flex', alignItems: 'center', background: 'white', cursor: 'pointer', border: '1px solid #E9ECEF' }}>
                        <ThemeIcon variant="light" size="lg" radius="md" mr="sm" color="blue">
                            <IconTrendingUp size={24} stroke={2.5} />
                        </ThemeIcon>
                        <div style={{ marginRight: 15 }}>
                            <Text size="xs" c="dimmed" fw={600}>달성률</Text>
                            <Text fw={800} size="lg" c="dark.9">85% 완료</Text>
                        </div>
                    </Paper>
                    <Button variant="white" color="blue" radius="md" rightSection={<IconChevronRight size={16} />}>
                        분석 리포트 보기
                    </Button>
                </Group>
            </Paper>

            {/* 2. ACTION GRID */}
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg" mb={40}>
                {/* Card 1 */}
                <Paper p="lg" radius="lg" withBorder style={{ cursor: 'pointer', transition: 'transform 0.2s', ':hover': { transform: 'translateY(-2px)' } } as any}>
                    <Group justify="space-between" align="flex-start" mb="lg">
                        <div>
                            <Title order={4} mb={5}>AI 리뷰 답글</Title>
                            <Text size="sm" c="dimmed">GPT가 추천하는<br />센스있는 답글</Text>
                        </div>
                        <ThemeIcon size={48} radius="md" variant="light" color="indigo">
                            <IconMessageChatbot size={28} />
                        </ThemeIcon>
                    </Group>
                    <Button fullWidth variant="light" color="indigo">댓글 관리하기</Button>
                </Paper>

                {/* Card 2 */}
                <Paper p="lg" radius="lg" withBorder>
                    <Group justify="space-between" align="flex-start" mb="lg">
                        <div>
                            <Title order={4} mb={5}>매출 분석</Title>
                            <Text size="sm" c="dimmed">어제 매출과<br />주간 트렌드 확인</Text>
                        </div>
                        <ThemeIcon size={48} radius="md" variant="light" color="teal">
                            <IconChartBar size={28} />
                        </ThemeIcon>
                    </Group>
                    <Button fullWidth variant="light" color="teal">매출 리포트</Button>
                </Paper>
            </SimpleGrid>

            {/* 3. SERVICE LIST */}
            <Text fw={700} size="lg" mb="md">추천 서비스</Text>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>

                {/* Item 1 */}
                <Paper p="md" radius="md" withBorder style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                    <ThemeIcon size={44} radius="md" color="orange" variant="light" mr="md">
                        <IconMapPin size={24} />
                    </ThemeIcon>
                    <div style={{ flexGrow: 1 }}>
                        <Text fw={600}>네이버 매장 정보 꾸미기</Text>
                        <Text size="xs" c="dimmed">플레이스 순위를 높이는 필수 정보 입력</Text>
                    </div>
                    <IconChevronRight color="#ced4da" />
                </Paper>

                {/* Item 2 */}
                <Paper p="md" radius="md" withBorder style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                    <ThemeIcon size={44} radius="md" color="grape" variant="light" mr="md">
                        <IconPencil size={24} />
                    </ThemeIcon>
                    <div style={{ flexGrow: 1 }}>
                        <Text fw={600}>블로그 마케팅 글쓰기</Text>
                        <Text size="xs" c="dimmed">AI가 써주는 홍보용 블로그 포스팅</Text>
                    </div>
                    <IconChevronRight color="#ced4da" />
                </Paper>

                {/* Item 3 */}
                <Paper p="md" radius="md" withBorder style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                    <ThemeIcon size={44} radius="md" color="blue" variant="light" mr="md">
                        <IconTruckDelivery size={24} />
                    </ThemeIcon>
                    <div style={{ flexGrow: 1 }}>
                        <Text fw={600}>식자재 최저가 주문</Text>
                        <Text size="xs" c="dimmed">사장님을 위한 B2B 마켓</Text>
                    </div>
                    <IconChevronRight color="#ced4da" />
                </Paper>

            </div>
        </Container>
    );
}
