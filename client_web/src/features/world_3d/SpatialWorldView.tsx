import React from 'react';
import { useSpatialWorldScene } from './useSpatialWorldScene';
import { SpatialWorldHud } from './SpatialWorldHud';
import { SpatialCatalogDrawer } from './SpatialCatalogDrawer';

export const SpatialWorldView: React.FC = () => {
  const {
    mountRef,
    worldState,
    speechText,
    isProcessing,
    spawnedProps,
    handleWeatherChange,
    spawnAssetInWorld,
    clearAllProps,
    handleCommandDispatch
  } = useSpatialWorldScene();

  return (
    <div className="relative w-full h-[calc(100vh-60px)] sm:h-[calc(100vh-64px)] overflow-hidden bg-[#030712] font-['Inter']">
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      <SpatialWorldHud
        worldState={worldState}
        speechText={speechText}
        isProcessing={isProcessing}
        onWeatherChange={handleWeatherChange}
        onSendCommand={handleCommandDispatch}
      />

      <SpatialCatalogDrawer
        spawnedProps={spawnedProps}
        onSpawnAsset={spawnAssetInWorld}
        onClearAll={clearAllProps}
      />
    </div>
  );
};

export default SpatialWorldView;
