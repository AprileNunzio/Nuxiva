import React, { useEffect, useState, useMemo } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  fetchStoreCatalog,
  fetchStoreRepositories,
  addStoreRepository,
  deleteStoreRepository,
  installPackage,
  uninstallPackage
} from './api';
import { StorePackage, StoreResources, StoreInstallResponse, StoreRepository } from './types';
import { StoreHeader } from './components/StoreHeader';
import { StoreHeroBanner } from './components/StoreHeroBanner';
import { StoreFilterBar } from './components/StoreFilterBar';
import { PackageCard } from './components/PackageCard';
import { RepositoriesView } from './components/RepositoriesView';
import { AddRepositoryModal } from './components/AddRepositoryModal';
import { MemoryAdvisoryModal } from './components/MemoryAdvisoryModal';
import { AddonsStepInstallerModal } from './components/AddonsStepInstallerModal';
import {
  Brain,
  Eye,
  Mic,
  Briefcase,
  Layers,
  Server,
  Globe,
  AlertCircle,
  X
} from 'lucide-react';

export function View() {
  const { t } = useScopedI18n('core_apps/store');
  const [packages, setPackages] = useState<StorePackage[]>([]);
  const [repositories, setRepositories] = useState<StoreRepository[]>([]);
  const [resources, setResources] = useState<StoreResources | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'packages' | 'repositories'>('packages');
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showStepInstaller, setShowStepInstaller] = useState(false);
  const [showAddRepoModal, setShowAddRepoModal] = useState(false);
  const [advisoryData, setAdvisoryData] = useState<{
    pkg: StorePackage;
    response: StoreInstallResponse;
  } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await fetchStoreCatalog();
      setPackages(data.packages || []);
      setResources(data.resources || null);
      if (data.repositories) {
        setRepositories(data.repositories);
      } else {
        const repos = await fetchStoreRepositories().catch(() => []);
        setRepositories(repos);
      }
    } catch {
      setErrorMsg(t('title'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleInstall = async (pkg: StorePackage, force: boolean = false) => {
    try {
      setBusyId(pkg.id);
      setErrorMsg(null);
      const res = await installPackage(pkg.id, force);
      if (res.advisory && res.can_force) {
        setAdvisoryData({ pkg, response: res });
        return;
      }
      setAdvisoryData(null);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err.message || t('insufficient_space'));
    } finally {
      setBusyId(null);
    }
  };

  const handleBatchInstall = async (selectedList: StorePackage[]) => {
    for (const pkg of selectedList) {
      await handleInstall(pkg, false);
    }
    setSelectedIds(new Set());
    await loadData();
  };

  const handleUninstall = async (pkg: StorePackage) => {
    try {
      setBusyId(pkg.id);
      setErrorMsg(null);
      await uninstallPackage(pkg.id);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err.message || t('core_package'));
    } finally {
      setBusyId(null);
    }
  };

  const toggleSelectPackage = (pkg: StorePackage) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(pkg.id)) {
        next.delete(pkg.id);
      } else {
        next.add(pkg.id);
      }
      return next;
    });
  };

  const handleAddRepository = async (data: { name: string; url: string; description?: string }) => {
    try {
      setErrorMsg(null);
      await addStoreRepository(data);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err.message || 'Errore durante il collegamento del repository.');
      throw err;
    }
  };

  const handleDeleteRepository = async (repoId: string) => {
    try {
      setLoading(true);
      setErrorMsg(null);
      await deleteStoreRepository(repoId);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err.message || 'Errore durante la rimozione del repository.');
    } finally {
      setLoading(false);
    }
  };

  const categories = [
    { id: 'all', label: t('cat_all'), icon: Layers },
    { id: 'intelligence', label: t('cat_intelligence'), icon: Brain },
    { id: 'vision', label: t('cat_vision'), icon: Eye },
    { id: 'audio', label: t('cat_audio'), icon: Mic },
    { id: 'productivity', label: t('cat_productivity'), icon: Briefcase },
    { id: 'system', label: t('cat_system'), icon: Server },
    { id: 'custom', label: t('cat_custom'), icon: Globe }
  ];

  const getCategoryCount = (catId: string) => {
    if (catId === 'all') return packages.length;
    if (catId === 'custom') return packages.filter(p => p.source === 'custom').length;
    return packages.filter(p => p.category === catId).length;
  };

  const filteredPackages = useMemo(() => {
    return packages.filter(pkg => {
      const matchCat =
        activeCategory === 'all'
          ? true
          : activeCategory === 'custom'
          ? pkg.source === 'custom'
          : pkg.category === activeCategory;
      const q = searchQuery.trim().toLowerCase();
      const matchQuery =
        !q ||
        pkg.title.toLowerCase().includes(q) ||
        pkg.description.toLowerCase().includes(q) ||
        (pkg.repository_name && pkg.repository_name.toLowerCase().includes(q));
      return matchCat && matchQuery;
    });
  }, [packages, activeCategory, searchQuery]);

  const featuredPackage = useMemo(() => {
    return packages.find(p => !p.installed && p.category === 'intelligence') || packages[0] || null;
  }, [packages]);

  const selectedPackagesList = useMemo(() => {
    return packages.filter(p => selectedIds.has(p.id));
  }, [packages, selectedIds]);

  return (
    <div className="flex flex-col h-full bg-transparent text-[var(--md-sys-color-on-surface)] overflow-hidden font-sans select-none relative">
      <StoreHeader
        t={t}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        packagesCount={packages.length}
        repositoriesCount={repositories.length}
        resources={resources}
        loading={loading}
        onRefresh={loadData}
        onOpenAddRepo={() => setShowAddRepoModal(true)}
      />

      {errorMsg && (
        <div className="md-enter mx-6 mt-3.5 flex items-center justify-between gap-3 rounded-2xl bg-error-container p-3 text-xs text-on-error-container">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="h-4 w-4 shrink-0 text-error" />
            <span className="leading-snug font-medium">{errorMsg}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMsg(null)}
            className="md-state rounded-full border-0 bg-transparent p-1 text-on-error-container"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {activeTab === 'packages' ? (
        <>
          <StoreHeroBanner
            featuredPackage={featuredPackage}
            selectedCount={selectedIds.size}
            onOpenStepInstaller={() => setShowStepInstaller(true)}
            onInstallFeatured={handleInstall}
            t={t}
          />

          <StoreFilterBar
            categories={categories}
            activeCategory={activeCategory}
            setActiveCategory={setActiveCategory}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            getCategoryCount={getCategoryCount}
            searchPlaceholder={t('search_placeholder')}
          />

          <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4.5 auto-rows-max">
            {filteredPackages.map(pkg => (
              <PackageCard
                key={pkg.id}
                pkg={pkg}
                isBusy={busyId === pkg.id}
                isSelected={selectedIds.has(pkg.id)}
                onToggleSelect={toggleSelectPackage}
                onInstall={() => handleInstall(pkg, false)}
                onUninstall={() => handleUninstall(pkg)}
                t={t}
              />
            ))}
          </div>
        </>
      ) : (
        <RepositoriesView
          repositories={repositories}
          packages={packages}
          onOpenAddRepo={() => setShowAddRepoModal(true)}
          onDeleteRepo={handleDeleteRepository}
          t={t}
        />
      )}

      {showStepInstaller && (
        <AddonsStepInstallerModal
          selectedPackages={selectedPackagesList}
          resources={resources}
          onClose={() => setShowStepInstaller(false)}
          onExecuteInstall={handleBatchInstall}
          t={t}
        />
      )}

      {showAddRepoModal && (
        <AddRepositoryModal
          onClose={() => setShowAddRepoModal(false)}
          onSubmit={handleAddRepository}
          t={t}
        />
      )}

      {advisoryData && (
        <MemoryAdvisoryModal
          advisoryData={advisoryData}
          resources={resources}
          onClose={() => setAdvisoryData(null)}
          onConfirmForce={pkg => handleInstall(pkg, true)}
          t={t}
        />
      )}
    </div>
  );
}
export default View;
