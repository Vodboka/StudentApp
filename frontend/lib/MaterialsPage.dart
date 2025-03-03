// ignore_for_file: file_names

import 'package:flutter/material.dart';
import 'MainPage.dart';
import 'FileDetailPage.dart';

class MaterialsPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Materials")),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center, // Center vertically
        children: [
          Expanded(
            child: FutureBuilder<List<String>>(
              future: fetchFiles(), // Fetch filenames from backend
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return Center(child: CircularProgressIndicator());
                } else if (snapshot.hasError) {
                  return Center(child: Text('Error loading files'));
                } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                  return Center(child: Text('No uploaded files yet.'));
                }

                return ListView(
                  padding: EdgeInsets.symmetric(horizontal: 20, vertical: 20),
                  shrinkWrap: true, // Prevents list from taking full space
                  children: snapshot.data!.map((fileName) {
                    String displayName = fileName.replaceAll(RegExp(r'\.[^.]+$'), '');
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8.0),
                      child: ElevatedButton(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => FileDetailPage(fileName: fileName),
                            ),
                          );
                        },
                        child: Text(displayName, textAlign: TextAlign.center),
                      ),
                    );
                  }).toList(),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
