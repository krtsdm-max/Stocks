import { ExpertTrackRecord } from '../components/Experts/ExpertTrackRecord';

export function ExpertsPage() {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Expert Track Record</h2>
        <p className="text-sm text-gray-500">
          Performance history, direction accuracy, and recommendation analytics for each expert.
        </p>
      </div>
      <ExpertTrackRecord />
    </div>
  );
}
