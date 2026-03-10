import AboutOpenData from '@/components/articles/AboutOpenData';
import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Sobre dados abertos - dados.gov',
    description: 'Saiba o que são dados abertos e qual a sua importância.',
};

export default function AboutOpenDataPage() {
    return <AboutOpenData />;
}
