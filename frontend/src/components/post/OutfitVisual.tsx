import {
  Footprints,
  Glasses,
  Layers,
  Shirt,
  ShoppingBag,
} from 'lucide-react'

import type {
  Outfit,
  OutfitItem,
} from '../../types/index'

interface OutfitVisualProps {
  outfit: Outfit

  imageUrl?: string

  matchScore?: number
}

function OutfitIcon({
  item,
}: {
  item: OutfitItem
}) {
  if (item.category === 'shoes') {
    return (
      <Footprints
        size={51}
        strokeWidth={1}
      />
    )
  }

  if (item.category === 'bag') {
    return (
      <ShoppingBag
        size={49}
        strokeWidth={1}
      />
    )
  }

  if (item.category === 'accessory') {
    return (
      <Glasses
        size={48}
        strokeWidth={1}
      />
    )
  }

  if (item.category === 'outerwear') {
    return (
      <Layers
        size={51}
        strokeWidth={1}
      />
    )
  }

  if (item.category === 'top') {
    return (
      <Shirt
        size={54}
        strokeWidth={1}
      />
    )
  }

  return (
    <svg
      width="52"
      height="58"
      viewBox="0 0 43 48"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.1"
      aria-hidden="true"
    >
      <path d="M9 3h25l3 41H24l-3-28-3 28H5L9 3Z M9 8h25" />
    </svg>
  )
}

export function OutfitVisual({
  outfit,
  imageUrl,
  matchScore,
}: OutfitVisualProps) {
  return (
    <div className="post-visual">
      {typeof matchScore === 'number' && (
        <div className="match-badge">
          {matchScore}% Match
        </div>
      )}

      {imageUrl ? (
        <img
          src={imageUrl}
          alt={`${outfit.name} 穿搭`}
          style={{
            display: 'block',
            width: '100%',
            aspectRatio: '4 / 4.3',
            objectFit: 'cover',
          }}
        />
      ) : (
        <div
          className="outfit-art"
          aria-label={`${outfit.name} 穿搭`}
        >
          {outfit.items
            .slice(0, 3)
            .map(item => (
              <div
                key={item.id}
                className="outfit-piece"
                style={{
                  backgroundColor:
                    item.color,
                }}
              >
                <OutfitIcon
                  item={item}
                />

                <span>
                  {item.name}
                </span>
              </div>
            ))}
        </div>
      )}
    </div>
  )
}