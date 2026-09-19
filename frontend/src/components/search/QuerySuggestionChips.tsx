interface QuerySuggestionChipsProps {
  suggestions: string[]
  onSelect: (suggestion: string) => void
}

export function QuerySuggestionChips({
  suggestions,
  onSelect,
}: QuerySuggestionChipsProps) {
  return (
    <div className="query-suggestions" aria-label="常用穿搭需求">
      {suggestions.map(suggestion => (
        <button
          key={suggestion}
          type="button"
          onClick={() => onSelect(suggestion)}
        >
          {suggestion}
        </button>
      ))}
    </div>
  )
}
