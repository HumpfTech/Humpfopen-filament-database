<script lang="ts">
	import { errorCount, warningCount, errorsByCategory } from '$lib/stores/validationStore';
	import { pathToRoute } from '$lib/utils/pathToRoute';
	import { goto } from '$app/navigation';
	import type { ValidationError } from '$lib/stores/validationStore';

	let isOpen = $state(false);

	function handleErrorClick(error: ValidationError) {
		if (error.path) {
			const route = pathToRoute(error.path);
			goto(route);
			isOpen = false;
		}
	}

	function toggleDropdown() {
		isOpen = !isOpen;
	}

	// Close dropdown when clicking outside
	function handleClickOutside(event: MouseEvent) {
		if (isOpen) {
			const target = event.target as HTMLElement;
			if (!target.closest('.validation-dropdown')) {
				isOpen = false;
			}
		}
	}
</script>

<svelte:window onclick={handleClickOutside} />

<div class="validation-dropdown relative">
	<button
		onclick={toggleDropdown}
		class="relative px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
	>
		<span>Validation</span>
		{#if $errorCount + $warningCount > 0}
			<span
				class="absolute -top-1 -right-1 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 rounded-full {$errorCount >
				0
					? 'bg-red-600'
					: 'bg-yellow-600'}"
			>
				{$errorCount + $warningCount}
			</span>
		{/if}
	</button>

	{#if isOpen}
		<div
			class="absolute right-0 mt-2 w-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 max-h-96 overflow-y-auto z-50"
		>
			{#if $errorCount + $warningCount === 0}
				<div class="p-4 text-center text-green-600 dark:text-green-400">
					<svg class="w-8 h-8 mx-auto mb-2" fill="currentColor" viewBox="0 0 20 20">
						<path
							fill-rule="evenodd"
							d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
							clip-rule="evenodd"
						/>
					</svg>
					<p>No validation issues</p>
				</div>
			{:else}
				{#each [...$errorsByCategory.entries()] as [category, errors]}
					<div class="border-b border-gray-200 dark:border-gray-700 last:border-b-0">
						<div class="bg-gray-50 dark:bg-gray-900 px-4 py-2">
							<h4 class="font-semibold text-sm text-gray-900 dark:text-white">
								{category}
								<span class="text-gray-500 dark:text-gray-400">({errors.length})</span>
							</h4>
						</div>
						<div class="divide-y divide-gray-100 dark:divide-gray-700">
							{#each errors.slice(0, 5) as error}
								<button
									class="w-full text-left px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors {error.level ===
									'ERROR'
										? 'border-l-4 border-red-500'
										: 'border-l-4 border-yellow-500'}"
									onclick={() => handleErrorClick(error)}
								>
									<div class="flex items-start gap-2">
										<span class="text-lg flex-shrink-0">
											{error.level === 'ERROR' ? '✗' : '⚠'}
										</span>
										<div class="flex-1 min-w-0">
											<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
												{error.message}
											</p>
											{#if error.path}
												<p class="text-xs text-gray-600 dark:text-gray-400 truncate">
													{error.path}
												</p>
											{/if}
										</div>
									</div>
								</button>
							{/each}
							{#if errors.length > 5}
								<div class="px-4 py-2 text-xs text-gray-500 dark:text-gray-400 text-center">
									... and {errors.length - 5} more
								</div>
							{/if}
						</div>
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>
