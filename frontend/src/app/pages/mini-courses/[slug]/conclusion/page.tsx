import React from 'react';
import MiniCourseCompletionClient from '@/components/mini-courses/MiniCourseCompletionClient';

export default async function ConclusionPage({
    params,
}: {
    params: Promise<{ slug: string }>;
}) {
    // In a real application, we would fetch the mini course data based on the slug
    // and verify that the user has completed the course
    const { slug } = await params;

    return <MiniCourseCompletionClient slug={slug} />;
}
