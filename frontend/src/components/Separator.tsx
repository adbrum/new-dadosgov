import React from 'react';

interface SeparatorProps {
    className?: string;
}

const Separator: React.FC<SeparatorProps> = ({ className = '' }) => {
    return (
        <div
            className={`w-full h-[2px] bg-[#E1E4EA] ${className}`}
            role="separator"
        />
    );
};

export default Separator;
