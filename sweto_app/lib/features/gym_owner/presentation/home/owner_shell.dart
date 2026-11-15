import 'package:flutter/material.dart';
import 'package:sweto_app/core/theme/colors.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/home_tab.dart';
import 'package:sweto_app/features/gym_owner/presentation/home/more_tab.dart';
import 'package:sweto_app/features/members/presentation/members_screen.dart';

/// Bottom tabs for a verified gym: Home, Members, More.
class OwnerShell extends StatefulWidget {
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
  State<OwnerShell> createState() => _OwnerShellState();
}

class _OwnerShellState extends State<OwnerShell> {
  final _home = GlobalKey<HomeTabState>();
  int _index = 0;

  void _select(int index) {
    setState(() => _index = index);
    // Numbers may have changed on another tab.
    if (index == 0) _home.currentState?.reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        bottom: false,
        child: IndexedStack(
          index: _index,
          children: [
            HomeTab(
              key: _home,
              gymId: widget.gymId,
              onLogout: widget.onLogout,
              now: widget.now,
            ),
            MembersScreen(gymId: widget.gymId),
            MoreTab(
              gymId: widget.gymId,
              gymName: widget.gymName,
              onLogout: widget.onLogout,
            ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        key: const Key('owner-tabs'),
        selectedIndex: _index,
        onDestinationSelected: _select,
        backgroundColor: AppColors.surface,
        indicatorColor: AppColors.primarySoft,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline),
            selectedIcon: Icon(Icons.people),
            label: 'Members',
          ),
          NavigationDestination(icon: Icon(Icons.menu), label: 'More'),
        ],
      ),
    );
  }
}
