import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sweto_app/core/router/app_routes.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/core/theme/radius.dart';
import 'package:sweto_app/core/theme/spacing.dart';
import 'package:sweto_app/core/theme/text_styles.dart';
import 'package:sweto_app/features/members/domain/member_entities.dart';
import 'package:sweto_app/features/members/presentation/export_share.dart';
import 'package:sweto_app/features/members/presentation/member_formatting.dart';
import 'package:sweto_app/features/members/presentation/members_providers.dart';
import 'package:sweto_app/shared/widgets/sweto_snackbar.dart';

const _pageSize = 30;

/// The verified gym's Finance tab: a month's revenue, cash vs M-Pesa, by
/// plan, a six-month trend and every payment in the month.
class FinanceTab extends ConsumerStatefulWidget {
  const FinanceTab({required this.gymId, super.key});

  final String gymId;

  @override
  ConsumerState<FinanceTab> createState() => FinanceTabState();
}

class FinanceTabState extends ConsumerState<FinanceTab> {
  /// Any day in the month shown; null for this month.
  DateTime? _month;
  FinanceSummary? _summary;
  String? _error;

  /// true M-Pesa only, false cash only, null both.
  bool? _mpesaOnly;
  List<FinanceTransaction> _transactions = const [];
  int _total = 0;
  bool _loadingMore = false;
  bool _exporting = false;

  /// Shares the month on screen as a CSV (date, member, plan, method, amount,
  /// receipt, recorded by).
  Future<void> _export(BuildContext buttonContext) async {
    if (_exporting) return;
    final box = buttonContext.findRenderObject() as RenderBox?;
    final origin = box == null
        ? null
        : box.localToGlobal(Offset.zero) & box.size;
    setState(() => _exporting = true);
    try {
      final file = await ref
          .read(membersRepositoryProvider)
          .exportPayments(widget.gymId, month: _month);
      await ref.read(exportSharerProvider)(file, origin: origin);
    } catch (error) {
      if (mounted) {
        showSwetoSnackBar(
          context,
          message: memberErrorMessage(error),
          type: SwetoSnackBarType.error,
        );
      }
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  @override
  void initState() {
    super.initState();
    reload();
  }

  /// Fetches the month again; the shell calls this when Finance is shown.
  Future<void> reload() async {
    final repo = ref.read(membersRepositoryProvider);
    try {
      final (summary, page) = await (
        repo.getFinance(widget.gymId, month: _month),
        repo.getFinanceTransactions(
          widget.gymId,
          month: _month,
          mpesa: _mpesaOnly,
          limit: _pageSize,
        ),
      ).wait;
      if (!mounted) return;
      setState(() {
        _summary = summary;
        _transactions = page.transactions;
        _total = page.total;
        _error = null;
      });
    } on ParallelWaitError<dynamic, dynamic> catch (error) {
      final cause = error.errors.$1 ?? error.errors.$2;
      if (mounted) setState(() => _error = memberErrorMessage(cause?.error));
    } catch (error) {
      if (mounted) setState(() => _error = memberErrorMessage(error));
    }
  }

  Future<void> _showMonth(DateTime month) async {
    setState(() => _month = month);
    await reload();
  }

  Future<void> _filter(bool? mpesaOnly) async {
    setState(() => _mpesaOnly = mpesaOnly);
    await reload();
  }

  Future<void> _loadMore() async {
    setState(() => _loadingMore = true);
    try {
      final page = await ref
          .read(membersRepositoryProvider)
          .getFinanceTransactions(
            widget.gymId,
            month: _month,
            mpesa: _mpesaOnly,
            limit: _pageSize,
            offset: _transactions.length,
          );
      if (mounted) {
        setState(() {
          _transactions = [..._transactions, ...page.transactions];
          _total = page.total;
        });
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(memberErrorMessage(error))));
      }
    } finally {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  Future<void> _openMember(String memberId) async {
    await context.pushNamed(
      AppRoutes.memberDetailName,
      pathParameters: {'gymId': widget.gymId, 'memberId': memberId},
    );
    if (mounted) reload();
  }

  @override
  Widget build(BuildContext context) {
    final summary = _summary;
    if (summary == null) {
      return Center(
        child: _error == null
            ? const CircularProgressIndicator(color: AppColors.primary)
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_error!, key: const Key('finance-error')),
                  const SizedBox(height: AppSpacing.sm),
                  OutlinedButton(onPressed: reload, child: const Text('Retry')),
                ],
              ),
      );
    }
    return RefreshIndicator(
      color: AppColors.primary,
      onRefresh: reload,
      child: ListView(
        key: const Key('finance-list'),
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
        children: [
          Row(
            children: [
              Expanded(
                child: Text('Finance', style: AppTextStyles.headingMedium),
              ),
              Builder(
                builder: (buttonContext) => TextButton.icon(
                  key: const Key('finance-export'),
                  onPressed: _exporting ? null : () => _export(buttonContext),
                  icon: _exporting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.ios_share, size: 18),
                  label: const Text('Export'),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          _monthSwitcher(summary),
          const SizedBox(height: AppSpacing.sm),
          _totalCard(summary),
          const SizedBox(height: AppSpacing.sm),
          _splitCard(summary),
          if (summary.failedMpesaCount > 0 || summary.pendingMpesaCount > 0)
            _mpesaNotice(summary),
          const SizedBox(height: AppSpacing.lg),
          Text('Last 6 months', style: AppTextStyles.titleLarge),
          const SizedBox(height: AppSpacing.xs),
          _TrendChart(
            trend: summary.trend,
            selected: summary.month,
            currency: summary.currency,
            onSelect: _showMonth,
          ),
          if (summary.byPlan.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.lg),
            Text('By plan', style: AppTextStyles.titleLarge),
            const SizedBox(height: AppSpacing.xs),
            for (final plan in summary.byPlan) _planRow(plan, summary),
          ],
          const SizedBox(height: AppSpacing.lg),
          Text('Payments', style: AppTextStyles.titleLarge),
          const SizedBox(height: AppSpacing.xs),
          _filters(),
          const SizedBox(height: AppSpacing.xs),
          if (_transactions.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
              child: Text(
                _mpesaOnly == null
                    ? 'No payments in ${formatMonth(summary.month)}.'
                    : 'No ${_mpesaOnly! ? 'M-Pesa' : 'cash'} payments in '
                          '${formatMonth(summary.month)}.',
                key: const Key('finance-no-payments'),
                style: AppTextStyles.bodySmall,
              ),
            )
          else
            for (final t in _transactions) _transactionRow(t),
          if (_transactions.length < _total)
            Center(
              child: TextButton(
                key: const Key('finance-load-more'),
                onPressed: _loadingMore ? null : _loadMore,
                child: Text(
                  _loadingMore
                      ? 'Loading…'
                      : 'Show more (${_total - _transactions.length})',
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _monthSwitcher(FinanceSummary summary) {
    final month = summary.month;
    return Row(
      children: [
        IconButton(
          key: const Key('finance-previous-month'),
          tooltip: 'Previous month',
          onPressed: () => _showMonth(DateTime(month.year, month.month - 1)),
          icon: const Icon(Icons.chevron_left, color: AppColors.textPrimary),
        ),
        Expanded(
          child: Text(
            formatMonth(month),
            key: const Key('finance-month'),
            textAlign: TextAlign.center,
            style: AppTextStyles.labelLarge,
          ),
        ),
        IconButton(
          key: const Key('finance-next-month'),
          tooltip: 'Next month',
          onPressed: summary.isCurrentMonth
              ? null
              : () => _showMonth(DateTime(month.year, month.month + 1)),
          icon: Icon(
            Icons.chevron_right,
            color: summary.isCurrentMonth
                ? AppColors.textMuted
                : AppColors.textPrimary,
          ),
        ),
      ],
    );
  }

  Widget _totalCard(FinanceSummary summary) {
    final change = summary.changePercent;
    final up = change != null && change >= 0;
    final span = summary.isCurrentMonth
        ? '1–${summary.through.day} ${shortMonth(summary.month)}'
        : formatMonth(summary.month);
    final against = summary.isCurrentMonth
        ? 'the same days last month'
        : 'the month before';
    return _Card(
      key: const Key('finance-total'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Revenue, $span', style: AppTextStyles.bodySmall),
          const SizedBox(height: 4),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              formatMoney(summary.total, summary.currency),
              style: AppTextStyles.headingLarge,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            summary.paymentsCount == 1
                ? '1 payment'
                : '${summary.paymentsCount} payments',
            style: AppTextStyles.caption,
          ),
          const SizedBox(height: 2),
          Text(
            change == null
                ? 'Nothing in $against to compare with'
                : '${up ? '↑' : '↓'} ${change.abs().toStringAsFixed(1)}% '
                      'vs $against',
            key: const Key('finance-change'),
            style: AppTextStyles.caption.copyWith(
              color: change == null
                  ? AppColors.textMuted
                  : up
                  ? AppColors.secondary
                  : AppColors.error,
            ),
          ),
        ],
      ),
    );
  }

  Widget _splitCard(FinanceSummary summary) {
    final total = summary.cashAmount + summary.mpesaAmount;
    final mpesaShare = total == 0 ? 0.0 : summary.mpesaAmount / total;
    Widget side(String label, double amount, int count, Color color, Key key) =>
        Expanded(
          child: Column(
            key: key,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: color,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(label, style: AppTextStyles.bodySmall),
                ],
              ),
              const SizedBox(height: 4),
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(
                  formatMoney(amount, summary.currency),
                  style: AppTextStyles.titleLarge,
                ),
              ),
              Text(
                count == 1 ? '1 payment' : '$count payments',
                style: AppTextStyles.caption,
              ),
            ],
          ),
        );
    return _Card(
      key: const Key('finance-split'),
      child: Column(
        children: [
          Row(
            children: [
              side(
                'M-Pesa',
                summary.mpesaAmount,
                summary.mpesaCount,
                AppColors.secondary,
                const Key('finance-mpesa'),
              ),
              const SizedBox(width: AppSpacing.sm),
              side(
                'Cash',
                summary.cashAmount,
                summary.cashCount,
                AppColors.primary,
                const Key('finance-cash'),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.pill),
            child: SizedBox(
              height: 8,
              child: total == 0
                  ? const ColoredBox(color: AppColors.border)
                  : Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Expanded(
                          flex: (mpesaShare * 1000).round(),
                          child: const ColoredBox(color: AppColors.secondary),
                        ),
                        Expanded(
                          flex: ((1 - mpesaShare) * 1000).round(),
                          child: const ColoredBox(color: AppColors.primary),
                        ),
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _mpesaNotice(FinanceSummary summary) {
    final parts = [
      if (summary.failedMpesaCount > 0)
        '${summary.failedMpesaCount} M-Pesa '
            '${summary.failedMpesaCount == 1 ? 'prompt' : 'prompts'} '
            'failed or cancelled',
      if (summary.pendingMpesaCount > 0)
        '${summary.pendingMpesaCount} still waiting',
    ];
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.xs),
      child: Row(
        key: const Key('finance-mpesa-notice'),
        children: [
          const Icon(Icons.info_outline, size: 16, color: AppColors.warning),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              '${parts.join(', ')}. Not counted in revenue.',
              style: AppTextStyles.caption,
            ),
          ),
        ],
      ),
    );
  }

  Widget _planRow(PlanRevenue plan, FinanceSummary summary) {
    final share = summary.total == 0 ? 0.0 : plan.amount / summary.total;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  plan.planName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              Text(
                formatMoney(plan.amount, summary.currency),
                style: AppTextStyles.labelMedium,
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.pill),
            child: LinearProgressIndicator(
              value: share,
              minHeight: 6,
              backgroundColor: AppColors.surfaceElevated,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            '${plan.count} ${plan.count == 1 ? 'payment' : 'payments'}',
            style: AppTextStyles.caption,
          ),
        ],
      ),
    );
  }

  Widget _filters() {
    Widget chip(String label, bool? value) => Padding(
      padding: const EdgeInsets.only(right: AppSpacing.xs),
      child: ChoiceChip(
        key: Key('finance-filter-$label'),
        label: Text(label),
        selected: _mpesaOnly == value,
        onSelected: (_) => _filter(value),
        selectedColor: AppColors.primary,
        backgroundColor: AppColors.surface,
        side: const BorderSide(color: AppColors.border),
        showCheckmark: false,
        labelStyle: AppTextStyles.labelMedium.copyWith(
          color: _mpesaOnly == value
              ? AppColors.white
              : AppColors.textSecondary,
        ),
      ),
    );
    return Row(
      children: [chip('All', null), chip('M-Pesa', true), chip('Cash', false)],
    );
  }

  Widget _transactionRow(FinanceTransaction t) {
    final paid = t.state == PaymentState.completed;
    final (statusLabel, statusColor) = switch (t.state) {
      PaymentState.completed => (null, AppColors.textPrimary),
      PaymentState.failed => ('Failed', AppColors.error),
      PaymentState.pending => ('Waiting', AppColors.warning),
    };
    // The receipt goes last so a narrow screen cuts it, not the date.
    final details = [
      formatDayTime(t.at),
      t.planName,
      t.isMpesa ? 'M-Pesa' : 'Cash',
      if (t.receipt != null) t.receipt!,
    ];
    return ListTile(
      key: Key('finance-payment-${t.paymentId}'),
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        backgroundColor: AppColors.surfaceElevated,
        child: Icon(
          t.isMpesa ? Icons.phone_iphone : Icons.payments_outlined,
          color: paid ? AppColors.primary : AppColors.textMuted,
          size: 20,
        ),
      ),
      title: Text(t.memberName, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text(
        details.join(' · '),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: AppTextStyles.bodySmall,
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            formatMoney(t.amount, t.currency),
            style: AppTextStyles.labelMedium.copyWith(
              color: paid ? AppColors.textPrimary : AppColors.textMuted,
              decoration: t.state == PaymentState.failed
                  ? TextDecoration.lineThrough
                  : null,
            ),
          ),
          if (statusLabel != null)
            Text(
              statusLabel,
              style: AppTextStyles.caption.copyWith(color: statusColor),
            ),
        ],
      ),
      onTap: () => _openMember(t.memberId),
    );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(AppSpacing.md),
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      border: Border.all(color: AppColors.border),
    ),
    child: child,
  );
}

/// Six monthly bars; tapping one shows that month.
class _TrendChart extends StatelessWidget {
  const _TrendChart({
    required this.trend,
    required this.selected,
    required this.currency,
    required this.onSelect,
  });

  final List<MonthRevenue> trend;
  final DateTime selected;
  final String currency;
  final ValueChanged<DateTime> onSelect;

  static const _barArea = 96.0;

  @override
  Widget build(BuildContext context) {
    final top = trend.fold<double>(0, (a, m) => m.amount > a ? m.amount : a);
    return _Card(
      key: const Key('finance-trend'),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (final m in trend)
            Expanded(
              child: Semantics(
                button: true,
                label:
                    '${formatMonth(m.month)}: ${formatMoney(m.amount, currency)}',
                child: InkWell(
                  key: Key('finance-trend-${m.month.year}-${m.month.month}'),
                  borderRadius: BorderRadius.circular(AppRadius.xs),
                  onTap: () => onSelect(m.month),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            _compact(m.amount),
                            style: AppTextStyles.caption,
                          ),
                        ),
                        const SizedBox(height: 4),
                        SizedBox(
                          height: _barArea,
                          child: Align(
                            alignment: Alignment.bottomCenter,
                            child: Container(
                              height: top == 0
                                  ? 3
                                  : 3 + (m.amount / top) * (_barArea - 3),
                              decoration: BoxDecoration(
                                color: _same(m.month)
                                    ? AppColors.primary
                                    : AppColors.surfaceElevated,
                                borderRadius: BorderRadius.circular(6),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          shortMonth(m.month),
                          style: AppTextStyles.caption.copyWith(
                            color: _same(m.month)
                                ? AppColors.textPrimary
                                : AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  bool _same(DateTime month) =>
      month.year == selected.year && month.month == selected.month;

  /// "254k", "1.2M", "900"
  static String _compact(double amount) {
    if (amount >= 1000000) {
      return '${(amount / 1000000).toStringAsFixed(1)}M';
    }
    if (amount >= 1000) return '${(amount / 1000).round()}k';
    return amount.round().toString();
  }
}
