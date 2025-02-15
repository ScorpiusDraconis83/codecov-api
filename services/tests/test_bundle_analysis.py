from unittest.mock import patch

import pytest
from django.test import TestCase
from shared.bundle_analysis import (
    BundleAnalysisReport,
    BundleAnalysisReportLoader,
    BundleChange,
    StoragePaths,
)
from shared.bundle_analysis.storage import get_bucket_name
from shared.storage.memory import MemoryStorageService

from core.tests.factories import CommitFactory, RepositoryFactory
from reports.models import CommitReport
from reports.tests.factories import CommitReportFactory
from services.archive import ArchiveService
from services.bundle_analysis import (
    BundleAnalysisComparison,
    BundleComparison,
    load_report,
)


@pytest.mark.django_db
@patch("services.bundle_analysis.get_appropriate_storage_service")
def test_load_report(get_storage_service):
    storage = MemoryStorageService({})
    get_storage_service.return_value = storage

    repo = RepositoryFactory()
    commit = CommitFactory(repository=repo)

    # no commit report record
    assert load_report(commit) is None

    commit_report = CommitReportFactory(
        commit=commit, report_type=CommitReport.ReportType.BUNDLE_ANALYSIS
    )

    storage_path = StoragePaths.bundle_report.path(
        repo_key=ArchiveService.get_archive_hash(repo),
        report_key=commit_report.external_id,
    )

    # nothing in storage
    assert load_report(commit) is None

    with open("./services/tests/samples/bundle_report.sqlite", "rb") as f:
        storage.write_file(get_bucket_name(), storage_path, f)

    report = load_report(commit)
    assert report is not None
    assert isinstance(report, BundleAnalysisReport)


class TestBundleComparison(TestCase):
    @patch("services.bundle_analysis.SharedBundleChange")
    def test_bundle_comparison(self, mock_shared_bundle_change):
        mock_shared_bundle_change = BundleChange(
            bundle_name="bundle1",
            change_type=BundleChange.ChangeType.ADDED,
            size_delta=1000000,
        )

        bundle_comparison = BundleComparison(
            mock_shared_bundle_change,
            7654321,
        )

        assert bundle_comparison.bundle_name == "bundle1"
        assert bundle_comparison.change_type == "added"
        assert bundle_comparison.size_delta == 1000000
        assert bundle_comparison.size_total == 7654321
        assert bundle_comparison.load_time_delta == 2.5
        assert bundle_comparison.load_time_total == 19.5


class TestBundleAnalysisComparison(TestCase):
    def setUp(self):
        self.repo = RepositoryFactory()

        self.base_commit = CommitFactory(repository=self.repo)
        self.base_commit_report = CommitReportFactory(
            commit=self.base_commit, report_type=CommitReport.ReportType.BUNDLE_ANALYSIS
        )

        self.head_commit = CommitFactory(repository=self.repo)
        self.head_commit_report = CommitReportFactory(
            commit=self.head_commit, report_type=CommitReport.ReportType.BUNDLE_ANALYSIS
        )

    @patch("services.bundle_analysis.get_appropriate_storage_service")
    def test_bundle_analysis_comparison(self, get_storage_service):
        storage = MemoryStorageService({})
        get_storage_service.return_value = storage

        with open("./services/tests/samples/base_bundle_report.sqlite", "rb") as f:
            storage_path = StoragePaths.bundle_report.path(
                repo_key=ArchiveService.get_archive_hash(self.repo),
                report_key=self.base_commit_report.external_id,
            )
            storage.write_file(get_bucket_name(), storage_path, f)

        with open("./services/tests/samples/head_bundle_report.sqlite", "rb") as f:
            storage_path = StoragePaths.bundle_report.path(
                repo_key=ArchiveService.get_archive_hash(self.repo),
                report_key=self.head_commit_report.external_id,
            )
            storage.write_file(get_bucket_name(), storage_path, f)

        loader = BundleAnalysisReportLoader(
            storage_service=storage,
            repo_key=ArchiveService.get_archive_hash(self.head_commit.repository),
        )

        bac = BundleAnalysisComparison(
            loader,
            self.base_commit_report.external_id,
            self.head_commit_report.external_id,
        )

        assert len(bac.bundles) == 5
        assert bac.size_delta == 36555
        assert bac.size_total == 201720
        assert bac.load_time_delta == 0.1
        assert bac.load_time_total == 0.5
