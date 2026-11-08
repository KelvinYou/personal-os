'use client';

import type { ReactNode } from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

interface AppearanceOption { id: string; label: string; description: string; icon: ReactNode; checked: boolean; onCheckedChange: () => void }
export function AppearanceMenu({ label, heading, icon, options }: { label: string; heading: string; icon: ReactNode; options: AppearanceOption[] }) {
  return (
    <DropdownMenu.Root modal={false}>
      <DropdownMenu.Trigger className="appearance-trigger" aria-label={label}>{icon}<span>{label}</span></DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="design-appearance-content" align="end" sideOffset={10} collisionPadding={12}>
          <DropdownMenu.Label className="design-menu-heading">{heading}</DropdownMenu.Label>
          {options.map(option => (
            <DropdownMenu.CheckboxItem key={option.id} id={option.id} checked={option.checked} onCheckedChange={option.onCheckedChange} onSelect={event => event.preventDefault()} className="design-appearance-item">
              <span className="design-menu-icon">{option.icon}</span><span className="design-menu-copy"><span>{option.label}</span><span className="design-menu-description">{option.description}</span></span><span className="design-switch" data-checked={option.checked} aria-hidden="true"><span /></span>
            </DropdownMenu.CheckboxItem>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
