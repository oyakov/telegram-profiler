import { useState } from 'react';
import useSWR from 'swr';
import api, { fetcher } from '../services/api';
import { useToast } from '../context/ToastContext';
import { useConfirm } from '../context/ConfirmContext';

export type LeadProfile = {
  first_name: string;
  last_name: string;
  company: string;
  position: string;
  keywords: string[];
  interests: string[];
  skills: string[];
  email: string;
  phone: string;
  min_score: number;
  min_activity_ratio: number;
  max_activity_ratio: number;
  created_after?: string;
  created_before?: string;
};

export type LeadSearch = {
  id: string;
  name: string;
  description?: string;
  profile_filter: LeadProfile;
  is_active: boolean;
  result_count: number;
  last_run_at?: string;
  created_at: string;
  updated_at: string;
};

export type LeadSearchResult = {
  total: number;
  contacts: any[];
};

export const useLeads = () => {
  const { showToast } = useToast();
  const { confirm } = useConfirm();

  const [profile, setProfile] = useState<LeadProfile>({
    first_name: '',
    last_name: '',
    company: '',
    position: '',
    keywords: [],
    interests: [],
    skills: [],
    email: '',
    phone: '',
    min_score: 10,
    min_activity_ratio: 0,
    max_activity_ratio: 100,
  });

  const [searchResults, setSearchResults] = useState<LeadSearchResult | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [savingSearch, setSavingSearch] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [searchName, setSearchName] = useState('');
  const [searchDescription, setSearchDescription] = useState('');

  const { data: savedSearches, mutate: mutateSavedSearches } = useSWR(
    '/api/leads/searches?active_only=true', fetcher
  );

  const handleSearch = async () => {
    setIsSearching(true);
    try {
      const res = await api.post('/api/leads/search', { ...profile, page: 1, page_size: 50 });
      setSearchResults(res.data);
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось выполнить поиск лидов');
    } finally {
      setIsSearching(false);
    }
  };

  const handleSaveSearch = async () => {
    if (!searchName.trim()) {
      showToast('error', 'Введите название поиска');
      return;
    }
    setSavingSearch(true);
    try {
      await api.post('/api/leads/searches', {
        name: searchName,
        description: searchDescription,
        profile_filter: { ...profile, page: 1, page_size: 50 },
      });
      setShowSaveDialog(false);
      setSearchName('');
      setSearchDescription('');
      mutateSavedSearches();
      showToast('success', 'Поиск сохранён');
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось сохранить поиск');
    } finally {
      setSavingSearch(false);
    }
  };

  const handleRunSavedSearch = async (searchId: string) => {
    setIsSearching(true);
    try {
      const res = await api.post(`/api/leads/searches/${searchId}/run`);
      setSearchResults(res.data);
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось запустить поиск');
    } finally {
      setIsSearching(false);
    }
  };

  const handleDeleteSavedSearch = async (searchId: string) => {
    if (!await confirm('Удалить сохранённый поиск?', 'Удаление поиска')) return;
    try {
      await api.delete(`/api/leads/searches/${searchId}`);
      mutateSavedSearches();
      showToast('success', 'Поиск удалён');
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Не удалось удалить поиск');
    }
  };

  const updateProfileField = (field: keyof LeadProfile, value: string | number | string[]) => {
    setProfile(prev => ({ ...prev, [field]: value }));
  };

  const addTag = (field: 'keywords' | 'interests', value: string) => {
    if (value.trim()) {
      setProfile(prev => ({ ...prev, [field]: [...prev[field], value.trim()] }));
    }
  };

  const removeTag = (field: 'keywords' | 'interests', index: number) => {
    setProfile(prev => ({ ...prev, [field]: prev[field].filter((_, i) => i !== index) }));
  };

  return {
    profile,
    searchResults,
    isSearching,
    savingSearch,
    savedSearches,
    showSaveDialog,
    searchName,
    searchDescription,
    setSearchName,
    setSearchDescription,
    setShowSaveDialog,
    handleSearch,
    handleSaveSearch,
    handleRunSavedSearch,
    handleDeleteSavedSearch,
    updateProfileField,
    addTag,
    removeTag,
  };
};
