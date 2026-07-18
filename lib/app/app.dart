import "package:flutter/material.dart";

class SwetoApp extends StatelessWidget {
  const SwetoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "SWETO",
      debugShowCheckedModeBanner: false,
      home: const Scaffold(body: Center(child: Text("SWETO"))),
    );
  }
}
