'use client';

import * as SelectPrimitive from '@radix-ui/react-select';

export interface SelectOption { value: string; label: string; description?: string; disabled?: boolean }
interface SelectProps { portalContainer?: HTMLElement | null; id?: string; name?: string; value: string; onValueChange: (value: string) => void; options: SelectOption[]; placeholder?: string; disabled?: boolean; className?: string; 'aria-label'?: string }
const emptyValue = '__design_empty_value__';
/** Local design-system Select. Business values are passed through without numeric coercion. */
export function Select({ portalContainer, id, name, value, onValueChange, options, placeholder = 'Choose an option', disabled, className = '', 'aria-label': ariaLabel }: SelectProps) {
  const selected = options.find(option => option.value === value);
  return (
    <SelectPrimitive.Root name={name} value={value === '' ? emptyValue : value} onValueChange={next => onValueChange(next === emptyValue ? '' : next)} disabled={disabled}>
      <SelectPrimitive.Trigger id={id} aria-label={ariaLabel} className={`design-select-trigger ${className}`}>
        <SelectPrimitive.Value><span className="design-select-value">{selected?.label || placeholder}</span></SelectPrimitive.Value>
        <SelectPrimitive.Icon className="design-select-chevron"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg></SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal container={portalContainer}>
        <SelectPrimitive.Content className="design-select-content" position="popper" sideOffset={6} align="start" collisionPadding={12}>
          <SelectPrimitive.Viewport className="design-select-viewport">
            {options.map(option => (
              <SelectPrimitive.Item key={option.value} value={option.value === '' ? emptyValue : option.value} disabled={option.disabled} className="design-select-item" textValue={option.label}>
                <div className="design-select-copy"><SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>{option.description && <span className="design-select-description">{option.description}</span>}</div>
                <SelectPrimitive.ItemIndicator className="design-select-check"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m20 6-11 11-5-5" /></svg></SelectPrimitive.ItemIndicator>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}
