import 'package:flutter/material.dart';
import 'main.dart';
import 'FileDetailPage.dart';
class FavouritesPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<String>>(
      future: fetchFiles(), // Function to fetch filenames from backend
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(child: CircularProgressIndicator());
        } else if (snapshot.hasError) {
          return Center(child: Text('Error loading files'));
        } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
          return Center(child: Text('No uploaded files yet.'));
        }

        return ListView(
          padding: EdgeInsets.all(10),
          children: snapshot.data!.map((fileName) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 4.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [ElevatedButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => FileDetailPage(fileName: fileName),
                      ),
                    );
                  },
                  child: Text(fileName, textAlign: TextAlign.center),
                ),
          ], ), );
          }).toList(),
        );
      },
    );
  }
}