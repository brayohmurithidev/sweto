import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/finance_tab.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/home_tab.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/more_tab.dart';
import 'package:sweto_app/features/members/presentation/members_screen.dart';
import 'package:sweto_app/features/staff/domain/staff_entities.dart';
import 'package:sweto_app/features/staff/presentation/staff_providers.dart';

/// Bottom tabs for a verified gym: Home, Members, Finance, More. Each tab
/// shows only if the person's role may use it.
class OwnerShell extends ConsumerStatefulWidget {
  const OwnerShell({
    required this.gymId,
    required this.gymName,
    required this.onLogout,
    this.now,
    super.key,
  });

  final String gymId;
  final String gymName;
  final VoidCallback onLogout;
  final DateTime Function()? now;

  @override
  ConsumerState<OwnerShell> createState() => _OwnerShellState();
}

class _OwnerShellState extends ConsumerState<OwnerShell> {
  final _home = GlobalKey<HomeTabState>();
  final _finance = GlobalKey<FinanceTabState>();
  _Tab _tab = _Tab.home;

  void _select(_Tab tab) {
    setState(() => _tab = tab);
    // Numbers may have changed on another tab.
    if (tab == _Tab.home) _home.currentState?.reload();
    if (tab == _Tab.finance) _finance.currentState?.reload();
  }

  @override
  Widget build(BuildContext context) {
    final access = ref.watch(gymAccessProvider);
    final tabs = [
      _Tab.home,
      if (access.can(GymPermission.viewMembers)) _Tab.members,
      if (access.can(GymPermission.viewFinance)) _Tab.finance,
      _Tab.more,
    ];
    final selected = tabs.contains(_tab) ? _tab : _Tab.home;
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        bottom: false,
        child: IndexedStack(
          index: tabs.indexOf(selected),
          children: [
            for (final tab in tabs)
              switch (tab) {
                _Tab.home => HomeTab(
                  key: _home,
                  gymId: widget.gymId,
                  onLogout: widget.onLogout,
                  now: widget.now,
                ),
                _Tab.members => MembersScreen(gymId: widget.gymId),
                _Tab.finance => FinanceTab(key: _finance, gymId: widget.gymId),
                _Tab.more => MoreTab(
                  gymId: widget.gymId,
                  gymName: widget.gymName,
                  onLogout: widget.onLogout,
                ),
              },
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        key: const Key('owner-tabs'),
        selectedIndex: tabs.indexOf(selected),
        onDestinationSelected: (index) => _select(tabs[index]),
        backgroundColor: AppColors.surface,
        indicatorColor: AppColors.primarySoft,
        destinations: [for (final tab in tabs) tab.destination],
      ),
    );
  }
}

enum _Tab {
  home(
    NavigationDestination(
      icon: Icon(Icons.home_outlined),
      selectedIcon: Icon(Icons.home),
      label: 'Home',
    ),
  ),
  members(
    NavigationDestination(
      icon: Icon(Icons.people_outline),
      selectedIcon: Icon(Icons.people),
      label: 'Members',
    ),
  ),
  finance(
    NavigationDestination(
      icon: Icon(Icons.account_balance_wallet_outlined),
      selectedIcon: Icon(Icons.account_balance_wallet),
      label: 'Finance',
    ),
  ),
  more(NavigationDestination(icon: Icon(Icons.menu), label: 'More'));

  const _Tab(this.destination);
  final NavigationDestination destination;
}
