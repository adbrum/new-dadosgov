import React from 'react';
import MiniCourseDetailClient from '@/components/mini-courses/MiniCourseDetailClient';

export default async function Page({
    params,
}: {
    params: Promise<{ slug: string }>;
}) {
    const { slug } = await params;

    return <MiniCourseDetailClient slug={slug} />;
}
