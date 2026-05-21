import React from 'react';
import { useLeads } from '../hooks/useLeads';
import LeadProfileConstructor from '../components/leads/LeadProfileConstructor';
import SavedSearchList from '../components/leads/SavedSearchList';
import LeadGrid from '../components/leads/LeadGrid';
import SaveSearchModal from '../components/leads/SaveSearchModal';
import './Leads.css';

const Leads: React.FC = () => {
  const {
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
    isLoadingSavedSearches,
  } = useLeads();

  return (
    <div className="leads-page">
      <div className="page-header-actions">
        <div>
          <h1 className="text-gradient">Поиск Лидов</h1>
          <p className="text-secondary">Конструктор профиля для целевого поиска среди выявленных лидов</p>
        </div>
      </div>

      <div className="leads-container">
        {/* Left: Lead Profile Constructor */}
        <LeadProfileConstructor 
          profile={profile}
          updateProfileField={updateProfileField}
          addTag={addTag}
          removeTag={removeTag}
          handleSearch={handleSearch}
          isSearching={isSearching}
          onSaveClick={() => setShowSaveDialog(true)}
        />

        {/* Right: Results and Saved Searches */}
        <div className="results-panel">
          <SavedSearchList 
            savedSearches={savedSearches}
            isLoading={isLoadingSavedSearches}
            onRun={handleRunSavedSearch}
            onDelete={handleDeleteSavedSearch}
            isSearching={isSearching}
          />

          <LeadGrid searchResults={searchResults} isSearching={isSearching} />
        </div>
      </div>

      {/* Save Search Modal */}
      <SaveSearchModal 
        isOpen={showSaveDialog}
        onClose={() => setShowSaveDialog(false)}
        searchName={searchName}
        setSearchName={setSearchName}
        searchDescription={searchDescription}
        setSearchDescription={setSearchDescription}
        onSave={handleSaveSearch}
        savingSearch={savingSearch}
      />
    </div>
  );
};

export default Leads;
