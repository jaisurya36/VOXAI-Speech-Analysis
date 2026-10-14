import { useQuery } from '@tanstack/react-query'
import { apiService } from '../services/api'

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => apiService.health(),
    refetchInterval: 30000,
    retry: false,
  })
}
