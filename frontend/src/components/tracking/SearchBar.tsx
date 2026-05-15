import React from 'react';
import { Search } from 'lucide-react';

interface SearchBarProps {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  placeholder?: string;
}

const SearchBar: React.FC<SearchBarProps> = ({ searchTerm, setSearchTerm, placeholder = "Поиск каналов..." }) => {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '12px 16px',
      background: 'rgba(30, 41, 59, 0.5)',
      border: '1px solid rgba(148, 163, 184, 0.15)',
      borderRadius: '8px',
      marginBottom: '20px'
    }}>
      <Search size={18} style={{ color: '#64748b' }} />
      <input
        type="text"
        placeholder={placeholder}
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        style={{
          flex: 1,
          background: 'transparent',
          border: 'none',
          color: '#f8fafc',
          outline: 'none',
          fontSize: '14px'
        }}
      />
    </div>
  );
};

export default SearchBar;
